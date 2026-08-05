"""
FastAPI dependency providers — HTTP layer only.

Routes inject dependencies via ``Depends()`` or ``Annotated`` aliases below.
Services, runner, and agents keep using ``app.persistence`` factories — they run
outside the request cycle (e.g. BackgroundTasks) where Depends does not apply.

Test overrides::

    app.dependency_overrides[get_repo] = lambda: FakeRepository()
"""

from typing import Annotated

from fastapi import Depends

from app.persistence import get_document_store, get_repository
from app.persistence.protocols import DataRepository, DocumentStorageRepository
from app.services.documents.upload_service import UploadService
from app.services.users.user_service import UserService
from app.services.workflows.workflow_service import WorkflowService


def get_repo() -> DataRepository:
    """Inject the active data repository (users, workflows, runs)."""
    return get_repository()


def get_doc_store() -> DocumentStorageRepository:
    """Inject the active document file storage backend."""
    return get_document_store()


def get_user_service(repo: DataRepository = Depends(get_repo)) -> UserService:
    return UserService(repo)


def get_workflow_service(
    repo: DataRepository = Depends(get_repo),
    users: UserService = Depends(get_user_service),
) -> WorkflowService:
    return WorkflowService(repo, users)


def get_upload_service(
    store: DocumentStorageRepository = Depends(get_doc_store),
) -> UploadService:
    return UploadService(store)


RepoDep = Annotated[DataRepository, Depends(get_repo)]
DocStoreDep = Annotated[DocumentStorageRepository, Depends(get_doc_store)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]


__all__ = [
    "DocStoreDep",
    "RepoDep",
    "UploadServiceDep",
    "UserServiceDep",
    "WorkflowServiceDep",
    "get_doc_store",
    "get_repo",
    "get_upload_service",
    "get_user_service",
    "get_workflow_service",
]
