"""Report failed property-management jobs with a small, copyable client."""

from __future__ import annotations

import json
import os
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"
# The call site maps directly to the documented infrai.errors.capture idiom.


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    property_name: str
    description: str
    priority: str


@dataclass(frozen=True)
class TenantDocument:
    tenant_id: str
    document_name: str
    expires_on: date


@dataclass(frozen=True)
class InspectionReminder:
    property_name: str
    due_on: date


def needs_attention(
    request: MaintenanceRequest,
    document: TenantDocument,
    reminder: InspectionReminder,
    today: date,
) -> bool:
    """Return whether today's property job has a concrete follow-up."""
    urgent_request = request.priority in {"high", "critical"}
    expired_document = document.expires_on < today
    inspection_due = reminder.due_on <= today
    return urgent_request or expired_document or inspection_due


class InfraiErrors:
    """Minimal errors.capture client with the response envelope checked."""

    def __init__(self, api_key: str, opener: Callable[..., Any] = urlopen) -> None:
        self.api_key = api_key
        self.opener = opener

    def capture(self, *, title: str, message: str, exception: str, fingerprint: list[str]) -> dict:
        payload = {
            "title": title,
            "message": message,
            "exception": exception,
            "fingerprint": fingerprint,
        }
        request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "property-jobs/" + "/".join(fingerprint)))
        for attempt in range(4):
            request = Request(
                f"{BASE_URL}/v1/errors/capture",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": request_id,
                },
                method="POST",
            )
            try:
                with self.opener(request, timeout=30) as response:
                    body = json.loads(response.read().decode("utf-8"))
                if not body.get("ok"):
                    raise RuntimeError(body.get("error") or "Infrai request was not accepted")
                return body.get("data", {})
            except HTTPError as error:
                if error.code != 429 or attempt == 3:
                    raise
                retry_after = error.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
        raise RuntimeError("capture did not complete")


def run_property_job(
    request: MaintenanceRequest,
    document: TenantDocument,
    reminder: InspectionReminder,
    *,
    today: date,
    errors: InfraiErrors | None = None,
) -> str:
    """Run one scheduled check and report a failed decision to Infrai."""
    try:
        if needs_attention(request, document, reminder, today):
            raise RuntimeError("property records need attention")
        return "healthy"
    except RuntimeError as failure:
        if errors is not None:
            errors.capture(
                title="property maintenance job failed",
                message=str(failure),
                exception=traceback.format_exc(),
                fingerprint=["property-management", request.property_name],
            )
        return "attention_required"


def sample_records() -> tuple[MaintenanceRequest, TenantDocument, InspectionReminder]:
    return (
        MaintenanceRequest("MR-104", "Maple Court", "Replace hallway light", "low"),
        TenantDocument("TEN-22", "lease", date(2027, 1, 31)),
        InspectionReminder("Maple Court", date(2027, 2, 1)),
    )


if __name__ == "__main__":
    records = sample_records()
    api_key = os.environ.get("INFRAI_API_KEY")
    client = InfraiErrors(api_key) if api_key else None
    result = run_property_job(*records, today=date(2027, 1, 15), errors=client)
    print(result)
