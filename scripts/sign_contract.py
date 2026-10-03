from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from nonprofit_signing.contract_workflow import ContractRequest, NonprofitContractWorkflow
from nonprofit_signing.signing_client import ContractApprovalClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark one nonprofit contract as approved")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--contract-id", required=True)
    parser.add_argument("--donor", required=True)
    parser.add_argument("--amount", required=True, type=Decimal)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--volunteer-shift", type=datetime.fromisoformat)
    args = parser.parse_args()

    result = NonprofitContractWorkflow(ContractApprovalClient()).approve(
        ContractRequest(
            contract_id=args.contract_id,
            donor_name=args.donor,
            donation_amount=args.amount,
            campaign_code=args.campaign,
            volunteer_shift_at=args.volunteer_shift,
        ),
        pdf=args.pdf.read_bytes(),
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
