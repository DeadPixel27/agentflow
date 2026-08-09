"""
FastAPI dependency providers — HTTP layer only.

Routes inject dependencies via ``Depends()`` or ``Annotated`` aliases below.
Services, runner, and agents keep using ``app.persistence`` factories — they run
outside the request cycle (e.g. BackgroundTasks) where Depends does not apply.

Test overrides::

    app.dependency_overrides[get_repo] = lambda: FakeRepository()
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.api.users import UserResponse as UserResponseModel
from app.persistence import get_document_store, get_repository, get_template_repository, get_user_template_store
from app.persistence.protocols import DataRepository, DocumentStorageRepository, TemplateRepository
from app.services.auth.jwt import InvalidTokenError, decode_access_token
from app.services.auth.service import AuthService
from app.services.documents.upload_service import UploadService
from app.services.email.inbound_service import InboundEmailService
from app.services.pipeline.refine_service import RefineService
from app.services.templates.template_master_refine_service import TemplateMasterRefineService
from app.services.templates.template_service import TemplateService
from app.services.templates.user_template_version_service import UserTemplateVersionService
from app.services.users.user_service import UserNotFoundError, UserService
from app.services.workflows.workflow_service import WorkflowService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_repo() -> DataRepository:
    """Inject the active data repository (users, workflows, runs)."""
    return get_repository()


def get_doc_store() -> DocumentStorageRepository:
    """Inject the active document file storage backend."""
    return get_document_store()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    repo: DataRepository = Depends(get_repo),
) -> UserResponseModel:
    """
    Extract and validate JWT from Authorization header (or access_token query).
    Returns the authenticated user. Raises 401 if missing/invalid.
    """
    token: Optional[str] = None
    if credentials is not None:
        token = credentials.credentials
    if not token:
        token = request.query_params.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user_id = payload["sub"]
    user_service = UserService(repo)
    try:
        user = user_service.fetch_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please sign in again.",
        ) from e

    response = UserResponseModel(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )
    request.state.current_user = response
    return response


def get_user_service(repo: DataRepository = Depends(get_repo)) -> UserService:
    return UserService(repo)


def get_workflow_service(
    repo: DataRepository = Depends(get_repo),
    users: UserService = Depends(get_user_service),
) -> WorkflowService:
    versions = UserTemplateVersionService(repo, get_user_template_store())
    return WorkflowService(repo, users, versions)


def get_upload_service(
    store: DocumentStorageRepository = Depends(get_doc_store),
) -> UploadService:
    return UploadService(store)


def get_auth_service(repo: DataRepository = Depends(get_repo)) -> AuthService:
    return AuthService(repo)


def get_refine_service(repo: DataRepository = Depends(get_repo)) -> RefineService:
    versions = UserTemplateVersionService(repo, get_user_template_store())
    return RefineService(repo, versions)


def get_version_service(repo: DataRepository = Depends(get_repo)) -> UserTemplateVersionService:
    return UserTemplateVersionService(repo, get_user_template_store())


def get_template_repo() -> TemplateRepository:
    return get_template_repository()


def get_master_refine_service(
    repo: DataRepository = Depends(get_repo),
    templates: TemplateRepository = Depends(get_template_repo),
) -> TemplateMasterRefineService:
    return TemplateMasterRefineService(repo, templates, get_user_template_store())


def get_template_service(
    templates: TemplateRepository = Depends(get_template_repo),
) -> TemplateService:
    return TemplateService(templates)


def get_inbound_email_service(
    repo: DataRepository = Depends(get_repo),
    store: DocumentStorageRepository = Depends(get_doc_store),
) -> InboundEmailService:
    return InboundEmailService(repo, store)


RepoDep = Annotated[DataRepository, Depends(get_repo)]
DocStoreDep = Annotated[DocumentStorageRepository, Depends(get_doc_store)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RefineServiceDep = Annotated[RefineService, Depends(get_refine_service)]
VersionServiceDep = Annotated[UserTemplateVersionService, Depends(get_version_service)]
MasterRefineServiceDep = Annotated[TemplateMasterRefineService, Depends(get_master_refine_service)]
TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
InboundEmailServiceDep = Annotated[InboundEmailService, Depends(get_inbound_email_service)]
CurrentUserDep = Annotated[UserResponseModel, Depends(get_current_user)]


__all__ = [
    "AuthServiceDep",
    "CurrentUserDep",
    "DocStoreDep",
    "InboundEmailServiceDep",
    "RepoDep",
    "UploadServiceDep",
    "UserServiceDep",
    "WorkflowServiceDep",
    "RefineServiceDep",
    "VersionServiceDep",
    "MasterRefineServiceDep",
    "TemplateServiceDep",
    "get_auth_service",
    "get_current_user",
    "get_doc_store",
    "get_inbound_email_service",
    "get_refine_service",
    "get_version_service",
    "get_master_refine_service",
    "get_repo",
    "get_template_repo",
    "get_template_service",
    "get_upload_service",
    "get_user_service",
    "get_workflow_service",
]
