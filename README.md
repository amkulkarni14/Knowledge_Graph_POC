# Enterprise Knowledge Graph Studio (prototype)

PostgreSQL tables **or several uploaded CSV files** → hybrid ontology (manual / rule-drafted + Groq AI,
human-approved, versioned) → NetworkX `MultiDiGraph` → validation gate → versioned graph store
(JSON + GraphML, optional Neo4j).
Every stage has its own module **and** its own screen that shows what it does, why, its input,
its output and what actually happened.

## Run

### First-time local setup with Docker

1. Clone the repository and open its root folder in a terminal.
2. Start Docker Desktop in Linux container mode, or use Docker Engine with the Compose plugin. Check that `docker info` shows a Server section.
3. From the repository root, run these PowerShell commands to build the app images and start the frontend, backend, PostgreSQL, and Neo4j.

   ```powershell
   cd docker
   if (!(Test-Path .env)) { Copy-Item .env.example .env }
   docker compose --profile postgres --profile neo4j up -d --build --wait
   ```

4. Open **http://127.0.0.1:8080** and sign in with **`admin` / `admin`** for local use. If port `8080` is unavailable, set `KG_WEB_PORT=18080` in `docker/.env`, rerun the Compose command, and open **http://127.0.0.1:18080**.

Docker starts the frontend and API for you. Each teammate can run their own copy with their own local database volumes. For PostgreSQL and Neo4j connection settings, see the [Docker setup guide](docker/README.md).

### Rebuild after code changes

Saving a source file does not update a running container. Pull the latest code or finish your local edits, then run the matching commands from the `docker/` folder.

| What changed | Commands |
|---|---|
| React frontend | `docker compose build frontend` then `docker compose up -d --no-deps frontend` |
| FastAPI backend or Python pipeline | `docker compose build backend` then `docker compose up -d --no-deps backend --wait` |
| Both app images | `docker compose --profile postgres --profile neo4j up -d --build --wait` |
| Runtime settings in `docker/.env` | `docker compose --profile postgres --profile neo4j up -d --wait` |

Refresh the browser after the container starts. Rebuilds preserve named volumes and saved artifacts. Recreating the backend clears active app sessions because those sessions live in memory.

For development outside Docker, see the [frontend](frontend/README.md) and [backend](backend/README.md) instructions.

### Run the pipeline from Python

Run the pipeline directly from the repository root with the Python requirements installed.

```powershell
python -m pip install -r requirements.txt
python scripts/run_pipeline.py --postgres
python scripts/run_pipeline.py --postgres --use-groq
python scripts/run_pipeline.py --csv-dir data/samples/customer360
```

## Folder structure

| Directory | Contents |
|---|---|
| `docker/` | Compose, Dockerfiles, and connection instructions |
| `frontend/` | React UI and browser tests |
| `backend/` | FastAPI API and tests |
| `data_pipeline/` | Pipeline implementation and tests |
| `data/` | Samples, fixtures, and ontology definitions |
| `database/postgres/` | PostgreSQL initialization SQL |
| `scripts/` | Command-line pipeline entry point |

## The stages

| # | Stage | Output |
|---|---|---|
| 1 | Data Sources | Read-only PostgreSQL connection or uploaded CSV files |
| 2 | Goal & Scope | Scope sheet (questions, tables, sensitive columns) |
| 3 | Schema extraction | SchemaCatalog from `pg_catalog` |
| 4 | Schema analysis | table types, relationship candidates, undeclared FKs |
| 5 | Manual ontology | draft: classes, attributes, relationships, mapping (hand-made, or **🪄 drafted from the schema by rules**) |
| 6 | Groq AI suggestions | labelled suggestions (valid / needs review / invalid) |
| 7 | Review & approve | hybrid draft (origin manual / ai / hybrid) |
| 8 | Ontology validation | structural + semantic report |
| 9 | Ontology versioning | approved immutable version (four-eyes), audit, rollback |
| 10 | Build plan | table/column → node/edge mapping |
| 11 | Data extraction | keyset batches, checkpoints, watermarks |
| 12 | Data quality | block / quarantine / warn findings, referential integrity |
| 13 | Clean & entity resolution | canonical records, merges, quarantine |
| 14 | Build NetworkX graph | `MultiDiGraph` (nodes pass, edges pass) |
| 15 | Graph validation | reconciliation + ontology conformance |
| 16 | Store graph | versioned snapshot, CURRENT pointer, optional Neo4j |

## Uploading CSV files

**Data Sources → CSV upload** takes several files at once. Each file becomes a table `csv.<file_name>`; everything
after source connection runs unchanged because the files sit behind the same read-only `DataSource` interface as PostgreSQL.
On the 7 bundled Customer 360 files the whole pipeline gives **54 nodes and 64 edges**, in any file order.

What is worked out from the files (rules only, no AI), and shown in Data Sources with every doubt listed as a warning:

| Step | Rule |
|---|---|
| Parse | UTF-8 (BOM) or Windows-1252; delimiter `, ; tab \|` read from the header; blank lines skipped; `""`, `null`, `none`, `nan`, `n/a` are NULL |
| Names | `Cust ID` → column `cust_id` (the original header is kept and shown in Stage 3); file name → table / class name |
| Types | bigint, double precision (also `4,500,000`), boolean `true/false`, date `YYYY-MM-DD`, timestamp; everything else text. Phone / account numbers, codes and numbers with leading zeros stay text |
| Key | an identifier column (`id`, `code`, `no`…) whose values are unique; else a composite such as `cust_id + score_date`; else a unique text column. A failing identifier (repeats, empty cells) is **reported, never replaced** by another column |
| Links | a column named like another file's key whose values match it becomes a foreign key (same name + overlap, or "mentions the file name" + ≥80 % overlap, flagged *values only*). Orphan values are reported and later set aside by Stage 12 |

Stage 5 → **🪄 Draft from the schema** then builds the ontology: a class per table that has a key, `Owner -[HAS_HOLDER]-> Holder`
per link (via the holder's rows), `A -[BRIDGE]-> B` per bridge table, and notes for everything it had to skip. The draft goes
through the same validation (Stage 8), four-eyes approval (Stage 9) and build (Stages 10-16) as a hand-made ontology.
The same button works for PostgreSQL schemas.

Safety: files live in memory only (never written to disk); limits `KG_MAX_UPLOAD_FILES` (25), `KG_MAX_UPLOAD_MB` (25 per file) and
`KG_MAX_UPLOAD_ROWS` (200 000 per file); only `.csv`, binary files refused, file names reduced to a safe table name,
cells that start with `= + - @` are reported and kept as text. **All files are checked before anything is loaded** — if one is bad
the upload is rejected with every reason and the previous connection stays as it was.

The AI step (Stage 6) is optional and requires a Groq key when enabled. Cleaning in Stage 13 handles spacing, case and merging of records; messy number or date formats
(`₹ 45,00,000`, `12/03/1985`, `8.5%`) must be fixed in the file — they are reported as warnings and kept as text.
`data/samples/customer360_messy` shows this: it is refused because its identifiers repeat.

## Design rules

* The builder never hard-codes a table or class; everything comes from the approved ontology.
* The AI only suggests: it sees structure (and optional masked samples, never PII), every
  suggestion is checked against the real schema, and a person decides. Builds never call the AI.
* Only an approved ontology version can be built; approval needs a passing validation and a
  reviewer different from the author.
* A graph becomes CURRENT only if Stage 15 passes. Bad rows are quarantined with a reason, never dropped.
* Table and column names reach SQL only after a catalog whitelist check and `psycopg.sql.Identifier` quoting.

## Not in this prototype yet

Incremental (watermark) graph updates and CDC, DuckDB "Silver" staging for very large tables,
moving the ontology repository from files into `kg_meta` in PostgreSQL, analytics / GraphRAG /
NL queries, authentication and role-based PII hiding.
