"""Uploaded CSV files as a read-only data source (several files -> one schema).

What it does, with rules only (no AI):
  1. parse every file safely (size / row / file-count limits, encoding, delimiter, binary check)
  2. give each file a table `csv.<file_name>` and each header a snake_case column name
  3. infer a column type (bigint, double precision, boolean, date, timestamp, text)
  4. infer each table's primary key (an identifier column, else a composite, else a unique column)
  5. infer the links between files: a column that holds the values of another file's key becomes a
     foreign key, so the rest of the pipeline sees the same SchemaCatalog it would get from PostgreSQL

The result is a `CsvSource`, which has exactly the interface of the other sources, so Stages 3-16 do
not know (or care) that the data came from files. Everything is held in memory and never written to disk.
All problems are reported as warnings so the user knows where to look; hard errors reject the whole upload
(nothing is half-loaded).
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import combinations
from pathlib import Path
from typing import Optional, Sequence

from kg_pipeline.core.naming import singularize
from kg_pipeline.core.naming import split_words
from kg_pipeline.core.naming import to_snake
from kg_pipeline.core.naming import unique_name
from kg_pipeline.core.schema_models import ColumnInfo
from kg_pipeline.core.schema_models import ForeignKey
from kg_pipeline.core.schema_models import SchemaCatalog
from kg_pipeline.core.schema_models import TableInfo
from kg_pipeline.preprocessing.connectors.sample_source import SampleSource

SCHEMA = "csv"
ALLOWED_EXTENSIONS = (".csv", ".tsv", ".txt")

NULL_TOKENS = frozenset({"", "null", "none", "nan", "n/a"})
_DELIMITERS = (",", ";", "\t", "|")

BIGINT, DOUBLE, BOOL, DATE, TS, TSTZ, TEXT = ("bigint", "double precision", "boolean", "date",
                                              "timestamp without time zone", "timestamp with time zone", "text")
_KEY_TYPES = {BIGINT, TEXT}                   # can identify a record on their own
_PART_TYPES = {BIGINT, TEXT, DATE, TS, TSTZ}  # can be part of a composite key

_ID_WORDS = frozenset({"id", "code", "number", "no", "num", "key", "ref", "reference", "uid", "uuid"})
_GENERIC_NAMES = frozenset({"id", "key", "code", "number", "no", "num", "name", "ref", "reference", "uid", "uuid"})
# numbers that are really labels: leading zeros / formatting matter and arithmetic means nothing
_LABEL_NUMBER_WORDS = frozenset({"no", "number", "num", "phone", "mobile", "zip", "pin", "pincode", "postal",
                                 "code", "ref", "reference", "aadhaar", "aadhar", "pan", "ssn"})
_SELF_REF_WORDS = frozenset({"parent", "manager", "supervisor", "referred", "referrer", "reports", "boss", "mentor"})

_INT = re.compile(r"[+-]?(0|[1-9]\d*)")
_FLOAT = re.compile(r"[+-]?((0|[1-9]\d*)(\.\d+)?|\.\d+)([eE][+-]?\d+)?")
_THOUSANDS = re.compile(r"[+-]?\d{1,3}(,\d{3})+(\.\d+)?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?")
_OTHER_DATE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")
_BOOL_TOKENS = frozenset({"true", "false"})

_MIN_NAME_MATCH_OVERLAP = 0.2     # same name as another file's key: the values must really overlap
_MIN_VALUE_MATCH_OVERLAP = 0.8    # different name: the values alone must overlap strongly
_MOSTLY = 0.6                     # a text column this much like numbers / dates is worth a hint to the user
_MAX_COMPOSITE = 3
_COMPOSITE_POOL = 6
_MAX_WARNINGS_PER_FILE = 12


class CsvImportError(ValueError):
    """The upload cannot be used. The message lists every problem, one per line."""


@dataclass(frozen=True)
class CsvUpload:
    filename: str
    content: bytes


@dataclass(frozen=True)
class UploadLimits:
    max_files: int = 25
    max_bytes: int = 25 * 1024 * 1024
    max_rows: int = 200_000

    @classmethod
    def from_settings(cls) -> "UploadLimits":
        from kg_pipeline.config import settings
        return cls(settings.max_upload_files, settings.max_upload_mb * 1024 * 1024, settings.max_upload_rows)


@dataclass
class FileReport:
    """What was understood about one uploaded file (shown in Stage 2)."""
    filename: str
    table: str
    rows: int
    columns: int
    key: list[str]
    key_how: str                                   # id | composite | unique | none
    delimiter: str
    links: list[str] = field(default_factory=list)  # "cust_id -> csv.customers.cust_id"
    link_specs: list[dict] = field(default_factory=list)   # the same, structured: column, to_table, to_column, basis
    warnings: list[str] = field(default_factory=list)

    def as_row(self) -> dict:
        return {"file": self.filename, "table": self.table, "rows": self.rows, "columns": self.columns,
                "key": ", ".join(self.key) or "(none found)", "links to": "; ".join(self.links) or "-",
                "warnings": len(self.warnings)}


# --------------------------------------------------------------------------- internal model
@dataclass(eq=False)
class _Col:
    header: str
    name: str
    sql_type: str
    values: list                       # typed values, None for NULL
    words: frozenset
    _canon: Optional[frozenset] = None

    def canon(self) -> frozenset:
        if self._canon is None:
            self._canon = frozenset(str(v).strip() for v in self.values if v is not None)
        return self._canon


@dataclass(eq=False)
class _Link:
    column: "_Col"
    owner: "_Table"
    owner_column: "_Col"
    by_values_only: bool


@dataclass(eq=False)
class _Table:
    filename: str
    name: str                          # csv.<table>
    words: list[str]                   # words of the file name, last one singular ("credit", "score")
    delimiter: str
    cols: list[_Col]
    nrows: int
    index: int = 0                     # position among the uploaded files
    key: list[_Col] = field(default_factory=list)
    key_how: str = "none"
    links: list[_Link] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        if len(self.warnings) < _MAX_WARNINGS_PER_FILE:
            self.warnings.append(f"{self.filename}: {message}")
        elif len(self.warnings) == _MAX_WARNINGS_PER_FILE:
            self.warnings.append(f"{self.filename}: more warnings were left out")


# --------------------------------------------------------------------------- 1. parsing
def _decode(raw: bytes) -> str:
    if b"\x00" in raw[:8192]:
        raise CsvImportError("this looks like a binary file, not a text CSV (save Excel files as CSV first)")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _detect_delimiter(text: str) -> str:
    """The delimiter that splits the header line into most fields (cells may contain other delimiters)."""
    header = text.splitlines()[0] if text.splitlines() else ""
    counts = {d: len(next(csv.reader([header], delimiter=d), [])) for d in _DELIMITERS}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 1 else ","


def _is_null(cell: str) -> bool:
    return cell.strip().lower() in NULL_TOKENS


def _parse(upload: CsvUpload, limits: UploadLimits) -> tuple[list[str], list[list[str]], str, list[str]]:
    """-> (headers, rows, delimiter, warnings). Raises CsvImportError."""
    if len(upload.content) > limits.max_bytes:
        raise CsvImportError(f"the file is larger than the {limits.max_bytes // (1024 * 1024)} MB limit")
    if not upload.content.strip():
        raise CsvImportError("the file is empty")
    text = re.sub(r"\A(?:[ \t]*\r?\n)+", "", _decode(upload.content))     # blank lines before the header row
    delimiter = _detect_delimiter(text)
    warnings: list[str] = []
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        headers = next(reader, [])
        width = len(headers)
        if not width:
            raise CsvImportError("the file has no header row")
        rows: list[list[str]] = []
        too_long = 0
        for line in reader:
            if not any(cell.strip() for cell in line):
                continue
            if len(rows) >= limits.max_rows:
                raise CsvImportError(f"the file has more than {limits.max_rows:,} rows (limit KG_MAX_UPLOAD_ROWS)")
            if len(line) > width:
                too_long += 1
            rows.append((line + [""] * width)[:width])
    except csv.Error as exc:
        raise CsvImportError(f"not valid CSV ({exc})") from exc
    if not rows:
        raise CsvImportError("the file has a header but no data rows")
    if too_long:
        warnings.append(f"{too_long} row(s) have more cells than the header; the extra cells were ignored")
    return headers, rows, delimiter, warnings


# --------------------------------------------------------------------------- 2. typing
def _unthousand(v: str) -> str:
    return v.replace(",", "") if _THOUSANDS.fullmatch(v) else v


def _parse_datetime(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def _type_column(header: str, raw: list[str], words: frozenset, table: _Table | None = None) -> tuple[str, list]:
    """The narrowest type that fits every non-null value, and the converted values."""
    present = [(i, c.strip()) for i, c in enumerate(raw) if not _is_null(c)]
    if not present:
        return TEXT, [None] * len(raw)
    texts = [v for _, v in present]

    def fill(convert) -> list:
        out: list = [None] * len(raw)
        for i, v in present:
            out[i] = convert(v)
        return out

    if all(v.lower() in _BOOL_TOKENS for v in texts):
        return BOOL, fill(lambda v: v.lower() == "true")

    cleaned = [_unthousand(v) for v in texts]
    if not words & _LABEL_NUMBER_WORDS:           # phone numbers, account numbers ... stay text
        if all(_INT.fullmatch(v) and abs(int(v)) < 2 ** 63 for v in cleaned):
            return BIGINT, fill(lambda v: int(_unthousand(v)))
        # ints and decimals mixed ("1500", "1500.50") are all read as decimals; a number is only a decimal
        # if at least one value really has a fraction or exponent (a 25-digit id must not lose digits)
        if all(_INT.fullmatch(v) or _FLOAT.fullmatch(v) for v in cleaned) \
                and any("." in v or "e" in v.lower() for v in cleaned):
            return DOUBLE, fill(lambda v: float(_unthousand(v)))

    if all(_DATE.fullmatch(v) for v in texts):
        try:
            return DATE, fill(date.fromisoformat)
        except ValueError:
            pass
    if all(_DATETIME.fullmatch(v) or _DATE.fullmatch(v) for v in texts):
        try:
            parsed = [_parse_datetime(v) for v in texts]
            if len({p.tzinfo is None for p in parsed}) == 1:
                return (TS if parsed[0].tzinfo is None else TSTZ), fill(_parse_datetime)
        except ValueError:
            pass

    if table is not None:
        _explain_text_column(table, header, texts)
    return TEXT, [None if _is_null(c) else c for c in raw]     # text keeps the original cell (cleaning is Stage 13)


def _explain_text_column(table: _Table, header: str, texts: list[str]) -> None:
    """Say why a column that looks like numbers or dates was kept as text (so the user can fix the file)."""
    n = len(texts)
    if n < 3:
        return
    numeric = {v for v in texts if _INT.fullmatch(_unthousand(v)) or _FLOAT.fullmatch(_unthousand(v))}
    dated = {v for v in texts if _DATE.fullmatch(v) or _DATETIME.fullmatch(v)}
    other = [v for v in texts if _OTHER_DATE.fullmatch(v)]
    if len(other) / n >= 0.8:
        table.warn(f"'{header}' looks like dates but not in YYYY-MM-DD form (e.g. '{other[0]}'); kept as text")
    for good, kind in ((numeric, "numbers"), (dated, "dates")):
        count = sum(v in good for v in texts)
        if _MOSTLY <= count / n < 1:
            bad = next(v for v in texts if v not in good)
            table.warn(f"'{header}' is mostly {kind} but {n - count} value(s) are not (e.g. '{bad}'); kept as text")


def _flag_formula_cells(table: _Table) -> None:
    """Cells that start with = + - @ are formulas if the data is ever opened in a spreadsheet. Report, keep as text."""
    count, example = 0, ""
    for col in table.cols:
        if col.sql_type != TEXT:
            continue
        for v in col.values:
            if v and (v[0] in "=@" or (v[0] in "+-" and len(v) > 1 and not _FLOAT.fullmatch(v))):
                count += 1
                example = example or v
    if count:
        table.warn(f"{count} cell(s) start with = + - or @ (e.g. '{example[:30]}'); they are kept as plain text, "
                   "but would be run as formulas if this data is opened in a spreadsheet")


# --------------------------------------------------------------------------- 3. keys
def _identifies(cols: Sequence[_Col], nrows: int) -> bool:
    """True when no two rows share the same values in these columns and none is empty."""
    seen = set()
    for cells in zip(*(c.values for c in cols)):
        if any(v is None for v in cells):
            return False
        canon = tuple(str(v).strip() for v in cells)
        if canon in seen:
            return False
        seen.add(canon)
    return nrows > 0


def _unique_identifiers(table: _Table) -> list[_Col]:
    """Identifier-like columns (id, code, no ...) whose values are all different and never empty."""
    return [c for c in table.cols if c.sql_type in _KEY_TYPES and c.words & _ID_WORDS
            and _identifies([c], table.nrows)]


def _choose_key(table: _Table, identifiers_elsewhere: set[str]) -> None:
    """`identifiers_elsewhere`: names that are a unique identifier in some OTHER file."""
    usable = [c for c in table.cols if c.sql_type in _KEY_TYPES]
    idish = [c for c in usable if c.words & _ID_WORDS]
    unique = {id(c) for c in usable if _identifies([c], table.nrows)}

    order = {id(c): i for i, c in enumerate(table.cols)}
    candidates = [c for c in idish if id(c) in unique]
    if candidates:
        # An identifier that is also a unique identifier in another file is probably that file's key, only
        # referenced here (one loan per customer makes loans.cust_id unique by chance), so it ranks last.
        # Otherwise identifiers come first in a file, so the first one wins.
        table.key, table.key_how = [min(candidates, key=lambda c: (c.name in identifiers_elsewhere, order[id(c)]))], "id"
        return

    # a record repeated over time is identified by who/what it is and when. Columns that are unique alone are
    # left out: a measure such as a score can be all different by chance and says nothing about the record.
    def pool_rank(c: _Col) -> int:
        if c.words & _ID_WORDS:
            return 0
        return 1 if c.sql_type in (DATE, TS, TSTZ) else 2
    pool = sorted((c for c in table.cols if c.sql_type in _PART_TYPES and id(c) not in unique), key=pool_rank)
    pool = pool[:_COMPOSITE_POOL]
    for size in range(2, _MAX_COMPOSITE + 1):
        for combo in combinations(pool, size):
            if any(c.words & _ID_WORDS for c in combo) and _identifies(combo, table.nrows):
                table.key, table.key_how = sorted(combo, key=lambda c: order[id(c)]), "composite"
                table.warn(f"no single column is unique, so {', '.join(repr(c.header) for c in table.key)} "
                           "together identify a row")
                return

    # No identifier-like column at all: a text column whose values are all different (an e-mail, a name) will do.
    # But if there IS an identifier column that fails (repeats, empty cells) that is a data problem to report, not
    # something to hide by promoting another column; and a number that happens to be unique is a measure, not a key.
    if not idish:
        for c in usable:
            if id(c) in unique and c.sql_type == TEXT:
                table.key, table.key_how = [c], "unique"
                table.warn(f"'{c.header}' was chosen as the key only because every value is different; "
                           "check that it identifies a record")
                return

    table.key, table.key_how = [], "none"
    if idish:
        col = idish[0]
        counts: dict[str, int] = {}
        for v in col.values:
            if v is not None:
                counts[str(v).strip()] = counts.get(str(v).strip(), 0) + 1
        repeated = {k: n for k, n in counts.items() if n > 1}
        nulls = sum(v is None for v in col.values)
        why = []
        if repeated:
            why.append(f"{len(repeated)} value(s) repeat (e.g. '{next(iter(repeated))}')")
        if nulls:
            why.append(f"{nulls} row(s) are empty")
        table.warn(f"no column identifies a row. '{col.header}' looks like the identifier but "
                   f"{' and '.join(why) or 'it is not unique'}. Fix the file; this table will not become a class")
    else:
        table.warn("no column or combination of columns identifies a row, so this table will not become a class")


# --------------------------------------------------------------------------- 4. links between files
def _spellings(owner: _Table, key: _Col) -> set[str]:
    stem = "_".join(owner.words)
    return {key.name, f"{stem}_{key.name}"}


def _overlap(col: _Col, key: _Col) -> float:
    values = col.canon()
    return len(values & key.canon()) / len(values) if values else 0.0


def _match(holder: _Table, col: _Col, owner: _Table, key: _Col) -> Optional[tuple[int, float, bool]]:
    """(rank, overlap, by_values_only) when `col` of `holder` holds the values of `owner`'s key."""
    if holder is owner and col is key:
        return None
    if holder is not owner and holder.key == [col] and (holder.nrows, -holder.index) >= (owner.nrows, -owner.index):
        return None       # two files keyed on the same thing are linked once: the smaller one (a subset, such as a
        #                   profile of customers) points at the larger; with equal rows the later file points at the earlier
    generic = col.name == key.name and col.name in _GENERIC_NAMES     # two files that both have an "id" are not linked
    name_match = not generic and col.name in _spellings(owner, key)
    overlap = _overlap(col, key)
    if name_match and holder is not owner:
        if col.canon() and overlap < _MIN_NAME_MATCH_OVERLAP:
            holder.warn(f"'{col.header}' has the same name as the key of {owner.filename} but only "
                        f"{overlap:.0%} of its values match, so it was not linked")
            return None
        return 0, overlap, False
    mentions_owner = set(owner.words) <= col.words
    mentions_self = holder is owner and bool(col.words & _SELF_REF_WORDS)
    if (mentions_owner or mentions_self) and overlap >= _MIN_VALUE_MATCH_OVERLAP:
        return 1, overlap, True
    return None


def _find_links(tables: list[_Table]) -> None:
    for holder in tables:
        for col in holder.cols:
            if col.sql_type not in _PART_TYPES:
                continue
            best: Optional[tuple] = None
            for owner in tables:
                if len(owner.key) != 1:
                    continue
                found = _match(holder, col, owner, owner.key[0])
                if found is None:
                    continue
                rank, overlap, by_values = found
                if best is None or (rank, -overlap) < (best[0], -best[1]):
                    best = (rank, overlap, by_values, owner)
            if best is None:
                continue
            _, _, by_values, owner = best
            link = _Link(col, owner, owner.key[0], by_values)
            holder.links.append(link)
            if by_values:
                holder.warn(f"'{col.header}' was linked to {owner.filename} only because its values match; "
                            "check the link")
            orphans = sorted(col.canon() - owner.key[0].canon())
            if orphans:
                holder.warn(f"{len(orphans)} value(s) of '{col.header}' have no match in {owner.filename} "
                            f"(e.g. '{orphans[0]}'); Stage 12 will set the affected links aside")


# --------------------------------------------------------------------------- the source
class CsvSource(SampleSource):
    """The uploaded files, behind the same read-only interface as every other source."""

    def __init__(self, catalog: SchemaCatalog, rows: dict[str, list[dict]], reports: list[FileReport]):
        super().__init__(catalog, rows)
        self.reports = reports

    @property
    def warnings(self) -> list[str]:
        return [w for r in self.reports for w in r.warnings]

    def ping(self) -> dict:
        return {"server_version": "uploaded CSV files (in memory, never written to disk)", "user": "upload",
                "read_only": True}


def _safe_filename(name: str) -> str:
    return re.split(r"[\\/]", name or "")[-1].strip() or "upload.csv"


def _build_table(upload: CsvUpload, limits: UploadLimits, taken: set[str], index: int) -> _Table:
    filename = _safe_filename(upload.filename)
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise CsvImportError(f"only {', '.join(ALLOWED_EXTENSIONS)} files are accepted")
    headers, raw_rows, delimiter, warnings = _parse(upload, limits)

    words = split_words(Path(filename).stem) or ["file"]
    words[-1] = singularize(words[-1])
    table_name = unique_name(to_snake(Path(filename).stem, "file"), taken)
    table = _Table(filename=filename, name=f"{SCHEMA}.{table_name}", words=words, delimiter=delimiter, cols=[],
                   nrows=len(raw_rows), index=index)
    for w in warnings:
        table.warn(w)

    used: set[str] = set()
    for i, header in enumerate(headers):
        header = header.strip() or f"column_{i + 1}"
        name = unique_name(to_snake(header, f"column_{i + 1}"), used)
        col_words = frozenset(split_words(header))
        raw = [row[i] for row in raw_rows]
        sql_type, values = _type_column(header, raw, col_words, table)
        table.cols.append(_Col(header, name, sql_type, values, col_words))
    _flag_formula_cells(table)
    return table


def build_csv_source(uploads: Sequence[CsvUpload], limits: UploadLimits | None = None) -> CsvSource:
    """Parse, type and link all files. Either every file is usable or CsvImportError lists what is wrong."""
    limits = limits or UploadLimits.from_settings()
    if not uploads:
        raise CsvImportError("choose at least one CSV file")
    if len(uploads) > limits.max_files:
        raise CsvImportError(f"at most {limits.max_files} files can be uploaded at once (got {len(uploads)})")

    tables: list[_Table] = []
    errors: list[str] = []
    taken: set[str] = set()
    for upload in uploads:
        try:
            tables.append(_build_table(upload, limits, taken, len(tables)))
        except CsvImportError as exc:
            errors.append(f"{_safe_filename(upload.filename)}: {exc}")
    if errors:
        raise CsvImportError("\n".join(errors))

    unique_ids = {id(t): {c.name for c in _unique_identifiers(t)} for t in tables}
    for t in tables:
        elsewhere = set().union(*(unique_ids[id(o)] for o in tables if o is not t))
        _choose_key(t, elsewhere)
    _find_links(tables)

    catalog_tables: dict[str, TableInfo] = {}
    rows: dict[str, list[dict]] = {}
    for t in tables:
        key_names = [c.name for c in t.key]
        # Other identifier columns that are unique become unique constraints - except a column that links to another
        # file: one loan per customer in a small file does not make "loan.cust_id" unique in general, and it would
        # turn a 1:N relationship into 1:1.
        linked = {id(l.column) for l in t.links}
        unique_cols = [[c.name] for c in t.cols if c not in t.key and id(c) not in linked
                       and c.sql_type in _KEY_TYPES and c.words & _ID_WORDS and _identifies([c], t.nrows)]
        catalog_tables[t.name] = TableInfo(
            name=t.name,
            columns={c.name: ColumnInfo(name=c.name, pg_type=c.sql_type, nullable=c not in t.key,
                                        source_header=c.header) for c in t.cols},
            primary_key=key_names, unique_constraints=unique_cols,
            foreign_keys=[ForeignKey(columns=[l.column.name], ref_table=l.owner.name,
                                     ref_columns=[l.owner_column.name]) for l in t.links])
        rows[t.name] = [{c.name: c.values[i] for c in t.cols} for i in range(t.nrows)]

    shown = ", ".join(t.filename for t in tables[:3]) + (f" +{len(tables) - 3} more" if len(tables) > 3 else "")
    catalog = SchemaCatalog(tables=catalog_tables, source_name=f"csv-upload://{shown}")
    reports = [FileReport(
        filename=t.filename, table=t.name, rows=t.nrows, columns=len(t.cols), key=[c.name for c in t.key],
        key_how=t.key_how, delimiter="tab" if t.delimiter == "\t" else t.delimiter,
        links=[f"{l.column.name} -> {l.owner.name}.{l.owner_column.name}" for l in t.links],
        link_specs=[{"column": l.column.name, "to_table": l.owner.name, "to_column": l.owner_column.name,
                     "basis": "values only" if l.by_values_only else "same column name + matching values"}
                    for l in t.links],
        warnings=t.warnings) for t in tables]
    return CsvSource(catalog, rows, reports)


def read_directory(path: str | Path) -> list[CsvUpload]:
    """The CSV files of a folder (used by the command line runner and the bundled samples)."""
    folder = Path(path)
    if not folder.is_dir():
        raise CsvImportError(f"folder not found: {folder}")
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS)
    if not files:
        raise CsvImportError(f"no .csv files in {folder}")
    return [CsvUpload(p.name, p.read_bytes()) for p in files]
