"""Inbound address management routes (CRUD for user's forwarding addresses)."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUserDep, InboundEmailServiceDep, RepoDep
from app.api.ownership import require_self, require_workflow_owner
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/inbound-addresses", tags=["inbound"])


class CreateInboundAddressRequest(BaseModel):
    workflow_id: str


class InboundAddressResponse(BaseModel):
    address_id: str
    full_address: str
    user_id: str
    workflow_id: str
    created_at: Optional[str] = None


@router.post("", response_model=InboundAddressResponse)
async def create_address(
    body: CreateInboundAddressRequest,
    inbound: InboundEmailServiceDep,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> InboundAddressResponse:
    workflow = repo.get_workflow(body.workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    require_workflow_owner(workflow, current_user)

    address = inbound.create_inbound_address(current_user.user_id, body.workflow_id)
    return InboundAddressResponse(
        address_id=address.address_id,
        full_address=address.full_address,
        user_id=address.user_id,
        workflow_id=address.workflow_id,
        created_at=address.created_at,
    )


@router.get("", response_model=list[InboundAddressResponse])
async def list_addresses(
    inbound: InboundEmailServiceDep,
    current_user: CurrentUserDep,
) -> list[InboundAddressResponse]:
    addresses = inbound.list_addresses(current_user.user_id)
    return [
        InboundAddressResponse(
            address_id=address.address_id,
            full_address=address.full_address,
            user_id=address.user_id,
            workflow_id=address.workflow_id,
            created_at=address.created_at,
        )
        for address in addresses
    ]


@router.delete("/{address_id}")
async def delete_address(
    address_id: str,
    inbound: InboundEmailServiceDep,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> dict[str, str]:
    address = repo.get_inbound_address(address_id)
    if address is None:
        raise HTTPException(status_code=404, detail="Inbound address not found")
    require_self(current_user, address.user_id)
    inbound.delete_address(address_id)
    return {"status": "deleted"}
