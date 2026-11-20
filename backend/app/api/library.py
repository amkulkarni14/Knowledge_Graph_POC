from fastapi import APIRouter, Request

from backend.app.core.dependencies import CurrentUser
from backend.app.dto.models import DomainRequest, Result, SavedDomain, SavedOntology
from backend.app.repositories import library

router = APIRouter(tags=["library"])


@router.get("/domains", response_model=Result[list[SavedDomain]])
def domains(request: Request, user: CurrentUser):
    return {"data": library.list_domains(request.app.state.config.storage_root, user.username)}


@router.post("/domains", status_code=201, response_model=Result[SavedDomain])
def create_domain(body: DomainRequest, request: Request, user: CurrentUser):
    return {"data": library.create_domain(request.app.state.config.storage_root, user.username, body)}


@router.get("/ontologies", response_model=Result[list[SavedOntology]])
def ontologies(request: Request, user: CurrentUser):
    return {"data": library.list_ontologies(request.app.state.config.storage_root, user.username)}
