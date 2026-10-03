from __future__ import annotations

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from .contract_workflow import ContractRequest, ContractResult, NonprofitContractWorkflow
from .signing_client import ContractApprovalClient, InfraiError, InfraiTransportError

app = FastAPI(title="Nonprofit Contract Approval")
workflow = NonprofitContractWorkflow(ContractApprovalClient())


@app.post("/contracts/sign", response_model=ContractResult)
async def sign_nonprofit_contract(
    contract: str = Form(),
    pdf: UploadFile = File(),
) -> ContractResult:
    try:
        request = ContractRequest.model_validate(json.loads(contract))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return workflow.approve(
            request,
            pdf=await pdf.read(),
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
