from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from nonprofit_signing.contract_workflow import ContractRequest, NonprofitContractWorkflow


class RecordingApprover:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def mark_approved(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"document_id": "signed-contract-42"}


def test_signed_contract_creates_receipt_reminder_and_campaign_tally() -> None:
    signer = RecordingApprover()
    workflow = NonprofitContractWorkflow(signer)
    shift = datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc)

    result = workflow.approve(
        ContractRequest(
            contract_id="contract-42",
            donor_name="Mina Chen",
            donation_amount=Decimal("125.50"),
            campaign_code="school-kits",
            volunteer_shift_at=shift,
        ),
        pdf=b"contract-pdf",
    )

    assert result.state == "approved"
    assert result.receipt.receipt_id == "receipt-contract-42"
    assert result.receipt.amount == Decimal("125.50")
    assert result.volunteer_reminder is not None
    assert result.volunteer_reminder.send_at == shift
    assert result.campaign_report.signed_contracts == 1
    assert result.campaign_report.donated_total == Decimal("125.50")
    assert signer.calls[0]["idempotency_key"] == "nonprofit-contract:contract-42"


def test_contract_without_shift_does_not_schedule_reminder() -> None:
    signer = RecordingApprover()
    workflow = NonprofitContractWorkflow(signer)

    result = workflow.approve(
        ContractRequest(
            contract_id="contract-43",
            donor_name="Alex Reed",
            donation_amount=Decimal("40.00"),
            campaign_code="school-kits",
        ),
        pdf=b"contract-pdf",
    )

    assert result.volunteer_reminder is None
