import json
import base64

import httpx

from nonprofit_signing.signing_client import ContractApprovalClient, InfraiError


def test_client_retries_rate_limit_and_reuses_idempotency_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {"code": "BUSY"}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"document_id": "signed-1"}, "error": None, "metadata": {}},
        )

    client = ContractApprovalClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = client.mark_approved(
        pdf=b"pdf",
        text="APPROVED",
        idempotency_key="contract:1",
    )

    assert result == {"document_id": "signed-1"}
    assert len(requests) == 2
    assert {request.headers["Idempotency-Key"] for request in requests} == {"contract:1"}
    for request in requests:
        assert request.headers["Content-Type"] == "application/json"
        assert json.loads(request.content) == {
            "pdf": base64.b64encode(b"pdf").decode("ascii"),
            "text": "APPROVED",
            "opacity": 0.18,
            "position": "center",
        }


def test_client_reads_rejection_envelope_before_http_status() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            400,
            content=json.dumps(
                {"ok": False, "data": None, "error": {"code": "BAD_INPUT", "message": "Check input"}, "metadata": {}}
            ),
        )
    )
    client = ContractApprovalClient(api_key="test-key", transport=transport)

    try:
        client.mark_approved(
            pdf=b"pdf",
            text="APPROVED",
            idempotency_key="contract:2",
        )
    except InfraiError as exc:
        assert exc.code == "BAD_INPUT"
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected InfraiError")
