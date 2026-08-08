"""Inbound address management routes (CRUD for user's forwarding addresses)."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import InboundEmailServiceDep

router = APIRouter(prefix="/api/inbound-addresses", tags=["inbound"])


class CreateInboundAddressRequest(BaseModel):
    user_id: str
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
) -> InboundAddressResponse:
    address = inbound.create_inbound_address(body.user_id, body.workflow_id)
    return InboundAddressResponse(
        address_id=address.address_id,
        full_address=address.full_address,
        user_id=address.user_id,
        workflow_id=address.workflow_id,
        created_at=address.created_at,
    )


@router.get("", response_model=list[InboundAddressResponse])
async def list_addresses(
    user_id: str,
    inbound: InboundEmailServiceDep,
) -> list[InboundAddressResponse]:
    addresses = inbound.list_addresses(user_id)
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
) -> dict[str, str]:
    inbound.delete_address(address_id)
    return {"status": "deleted"}
