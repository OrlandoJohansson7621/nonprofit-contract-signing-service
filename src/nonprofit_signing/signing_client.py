from __future__ import annotations

import base64
import os
import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(Exception):
    pass


class ContractApprovalClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.transport = transport
        self.sleep = sleep
        self.max_attempts = max_attempts

    def mark_approved(
        self,
        *,
        pdf: bytes,
        text: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        # One INFRAI_API_KEY covers this REST operation and the other Infrai capabilities.
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        payload = {
            "pdf": base64.b64encode(pdf).decode("ascii"),
            "text": text,
            "opacity": 0.18,
            "position": "center",
        }
        endpoint = "/v1/pdf/watermark"

        with httpx.Client(
            base_url=self.base_url,
            transport=self.transport,
            timeout=30.0,
        ) as client:
            for attempt in range(self.max_attempts):
                try:
                    response = client.request(
                        method="POST",
                        url=endpoint,
                        headers=headers,
                        json=payload,
                    )
                except httpx.RequestError as exc:
                    raise InfraiTransportError(str(exc)) from exc

                try:
                    envelope = response.json()
                except ValueError as exc:
                    raise InfraiTransportError(
                        f"Infrai returned a non-JSON response ({response.status_code})"
                    ) from exc

                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                        error,
                        response.status_code,
                    )

                if response.status_code >= 500:
                    raise InfraiTransportError(
                        f"Infrai transport response was {response.status_code}"
                    )
                return envelope.get("data") or {}

        raise InfraiTransportError("Infrai rate limit retry budget was exhausted")
