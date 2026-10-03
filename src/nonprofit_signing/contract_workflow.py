from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ContractRequest(BaseModel):
    contract_id: str = Field(min_length=1)
    donor_name: str = Field(min_length=1)
    donation_amount: Decimal = Field(gt=0)
    campaign_code: str = Field(min_length=1)
    volunteer_shift_at: datetime | None = None
    approval_text: str = "APPROVED"


class DonorReceipt(BaseModel):
    receipt_id: str
    donor_name: str
    amount: Decimal
    campaign_code: str


class VolunteerReminder(BaseModel):
    contract_id: str
    send_at: datetime


class CampaignReport(BaseModel):
    campaign_code: str
    signed_contracts: int
    donated_total: Decimal


class ContractResult(BaseModel):
    contract_id: str
    state: str
    approved_pdf: dict[str, Any]
    receipt: DonorReceipt
    volunteer_reminder: VolunteerReminder | None
    campaign_report: CampaignReport


@dataclass
class _CampaignTally:
    signed_contracts: int = 0
    donated_total: Decimal = Decimal("0")


class NonprofitContractWorkflow:
    def __init__(self, signer: Any) -> None:
        self.signer = signer
        self._campaigns: dict[str, _CampaignTally] = {}

    def approve(
        self,
        request: ContractRequest,
        *,
        pdf: bytes,
    ) -> ContractResult:
        approved_pdf = self.signer.mark_approved(
            pdf=pdf,
            text=request.approval_text,
            idempotency_key=f"nonprofit-contract:{request.contract_id}",
        )

        tally = self._campaigns.setdefault(request.campaign_code, _CampaignTally())
        tally.signed_contracts += 1
        tally.donated_total += request.donation_amount

        reminder = None
        if request.volunteer_shift_at is not None:
            reminder = VolunteerReminder(
                contract_id=request.contract_id,
                send_at=request.volunteer_shift_at,
            )

        return ContractResult(
            contract_id=request.contract_id,
            state="approved",
            approved_pdf=approved_pdf,
            receipt=DonorReceipt(
                receipt_id=f"receipt-{request.contract_id}",
                donor_name=request.donor_name,
                amount=request.donation_amount,
                campaign_code=request.campaign_code,
            ),
            volunteer_reminder=reminder,
            campaign_report=CampaignReport(
                campaign_code=request.campaign_code,
                signed_contracts=tally.signed_contracts,
                donated_total=tally.donated_total,
            ),
        )
