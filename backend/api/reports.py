"""VisionOps AI — Reports API Endpoints.

Exposes report generation endpoints over HTTP. These routes are a thin
boundary over :class:`~backend.services.report_service.ReportService` and
use the existing report schemas from :mod:`backend.schemas.report`.

Implemented endpoints:
    - ``POST   /reports/generate`` — generate a report in the specified format.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_report_service
from backend.schemas.report import ReportRequest, ReportResponse
from backend.services import ReportService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=201,
    summary="Generate a report",
    description=(
        "Generates a report in the specified format (PDF, Excel, CSV, "
        "or JSON) with optional filters for video ID, date range, and "
        "data sections to include."
    ),
)
async def generate_report(
    payload: ReportRequest,
    report_service: Annotated[
        ReportService, Depends(get_report_service)
    ] = ...,
) -> Any:
    """Generate a report in the specified format.

    Args:
        payload: Validated report request with format and filters.
        report_service: Injected report service.

    Returns:
        :class:`ReportResponse` with report metadata.
    """
    filters: dict[str, Any] = {}
    if payload.video_id:
        filters["video_ids"] = [payload.video_id]
    if payload.date_from:
        filters["date_from"] = payload.date_from
    if payload.date_to:
        filters["date_to"] = payload.date_to

    options: dict[str, Any] = {}
    if payload.title:
        options["title"] = payload.title

    result = await report_service.generate_report(
        format=payload.format.value,
        filters=filters,
        options=options,
    )

    return ReportResponse(
        report_id=result.get("report_id", ""),
        format=result.get("format", payload.format.value),
        status=result.get("status", "generated"),
        file_path=result.get("file_path", ""),
        file_size=result.get("file_size"),
        title=payload.title,
        message=result.get("message", "Report generated successfully."),
        generated_at=result.get("generated_at", ""),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]
