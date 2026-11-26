"""Account-scoped domain templates and ownership of durable workspace artifacts."""
import json
import sqlite3
from contextlib import closing, contextmanager
from uuid import uuid4

from kg_pipeline.core.ontology_models import Ontology
from kg_pipeline.ontology_compiler.s09_ontology_repository import OntologyRepository, write_ontology


@contextmanager
def catalog(root):
    root.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(root / "library.sqlite3")) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS domain (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS workspace (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL
        )""")
        yield db


def register_workspace(root, workspace_id, owner, name):
    with catalog(root) as db:
        db.execute("INSERT INTO workspace VALUES (?, ?, ?)", (str(workspace_id), owner, name))


def create_domain(root, owner, domain):
    domain_id = str(uuid4())
    with catalog(root) as db:
        db.execute("INSERT INTO domain VALUES (?, ?, ?)", (domain_id, owner, domain.model_dump_json()))
    return {"id": domain_id, **domain.model_dump()}


def list_domains(root, owner):
    with catalog(root) as db:
        rows = db.execute("SELECT id, payload FROM domain WHERE owner = ?", (owner,)).fetchall()
    return sorted(({"id": key, **json.loads(payload)} for key, payload in rows),
                  key=lambda domain: (domain["name"].casefold(), domain["id"]))


def save_working_draft(root, ontology):
    directory = root / "working_drafts"
    directory.mkdir(parents=True, exist_ok=True)
    write_ontology(directory / f"{ontology.ontology_id}.json", ontology)


def list_ontologies(root, owner):
    with catalog(root) as db:
        workspaces = db.execute("SELECT id, name FROM workspace WHERE owner = ? ORDER BY name, id",
                                (owner,)).fetchall()
    results = []
    for workspace_id, workspace_name in workspaces:
        workspace = root / workspace_id
        repository = workspace / "ontology_repo"
        ontologies = {}
        if repository.is_dir():
            repo = OntologyRepository(repository)
            for ontology_id in repo.ontology_ids():
                versions = [repo.get(ontology_id, version) for version in reversed(repo.versions(ontology_id))]
                if versions:
                    ontologies[ontology_id] = (versions[0].name, [summary(item, item.version) for item in versions])
        for path in sorted((workspace / "working_drafts").glob("*.json")):
            draft = Ontology.model_validate_json(path.read_text(encoding="utf-8"))
            _, versions = ontologies.get(draft.ontology_id, (draft.name, []))
            versions.append(summary(draft, None))
            ontologies[draft.ontology_id] = (draft.name, versions)
        results.extend({"workspace_id": workspace_id, "workspace_name": workspace_name,
                        "ontology_id": ontology_id, "name": name, "versions": versions}
                       for ontology_id, (name, versions) in ontologies.items())
    return results


def summary(ontology, version):
    return {"version": version, "status": ontology.status.value,
            "classes": len(ontology.classes), "relationships": len(ontology.relationships)}
