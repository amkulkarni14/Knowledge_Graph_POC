"""Turns arbitrary file / column / table names into the identifiers the ontology model requires.

* attribute names  -> snake_case              (ATTR_NAME_RE)
* class names      -> PascalCase, singular    (CLASS_NAME_RE)
* relationship     -> UPPER_SNAKE_CASE        (REL_NAME_RE)
"""
from __future__ import annotations

import re
import unicodedata

NAME_LIMIT = 63


def split_words(text: str) -> list[str]:
    """'Cust ID' / 'cust_id' / 'CustID' / 'CreditScore' -> lowercase words."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return [w.lower() for w in re.split(r"[^0-9A-Za-z]+", text) if w]


def to_snake(text: str, fallback: str = "column") -> str:
    """A name that is valid as an ontology attribute / SQL identifier part: ^[a-z][a-z0-9_]{0,62}$."""
    name = "_".join(split_words(text)) or fallback
    if not name[0].isalpha():
        name = f"c_{name}"
    return name[:NAME_LIMIT]


_IRREGULAR = {"people": "person", "children": "child", "men": "man", "women": "woman", "indices": "index",
              "analyses": "analysis", "statuses": "status", "addresses": "address", "data": "data"}


def singularize(word: str) -> str:
    """Naive English singular, good enough for table names ('status' and 'address' are left alone)."""
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    if word.endswith(("ss", "us", "is")):
        return word
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def to_class_name(table: str) -> str:
    """'csv.credit_scores' -> 'CreditScore'  (only the last word is made singular)."""
    words = split_words(table.split(".")[-1]) or ["record"]
    words[-1] = singularize(words[-1])
    name = "".join(w.capitalize() for w in words)
    if not name[0].isalpha():
        name = f"N{name}"
    return name[:NAME_LIMIT]


def to_upper_snake(text: str, fallback: str = "RELATED_TO") -> str:
    name = "_".join(split_words(text)).upper() or fallback
    if not name[0].isalpha():
        name = f"R_{name}"
    return name[:NAME_LIMIT]


def unique_name(base: str, taken: set[str], sep: str = "_") -> str:
    """base, base_2, base_3 ... (keeps the result inside the length limit) and records it in `taken`."""
    name, n = base, 2
    while name in taken:
        suffix = f"{sep}{n}"
        name, n = base[: NAME_LIMIT - len(suffix)] + suffix, n + 1
    taken.add(name)
    return name
