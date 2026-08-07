"""Public persistence API — routes and services import from here only."""

from app.persistence.registry import (
    get_data_backend_name,
    get_document_backend_name,
    get_document_store,
    get_repository,
    get_template_backend_name,
    get_template_repository,
    get_user_template_backend_name,
    get_user_template_store,
)

# Backward-compatible module-level functions (delegate to active repository)
def save_user(user):
    get_repository().save_user(user)


def get_user(user_id):
    return get_repository().get_user(user_id)


def list_users():
    return get_repository().list_users()


def save_run(run):
    get_repository().save_run(run)


def get_run(run_id):
    return get_repository().get_run(run_id)


def list_runs_by_workflow(workflow_id):
    return get_repository().list_runs_by_workflow(workflow_id)


def save_workflow(workflow):
    get_repository().save_workflow(workflow)


def get_workflow(workflow_id):
    return get_repository().get_workflow(workflow_id)


def list_workflows(user_id=None):
    return get_repository().list_workflows(user_id=user_id)


__all__ = [
    "get_repository",
    "get_document_store",
    "get_template_repository",
    "get_user_template_store",
    "get_data_backend_name",
    "get_document_backend_name",
    "get_template_backend_name",
    "get_user_template_backend_name",
    "save_user",
    "get_user",
    "list_users",
    "save_run",
    "get_run",
    "list_runs_by_workflow",
    "save_workflow",
    "get_workflow",
    "list_workflows",
]
