"""VisionOps AI — Settings API Endpoints.

Exposes application configuration read, update, validation, and reset
endpoints over HTTP. These routes are a thin boundary over
:class:`~backend.services.settings_service.SettingsService` and use the
existing settings schemas from :mod:`backend.schemas.settings`.

Implemented endpoints:
    - ``GET    /settings`` — retrieve current configuration.
    - ``PUT    /settings`` — update configuration settings.
    - ``POST   /settings/validate`` — validate a setting value.
    - ``POST   /settings/reset`` — reset settings to defaults.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_settings_service
from backend.schemas.settings import SettingsResponse, SettingsUpdate
from backend.services import SettingsService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/settings", tags=["Settings"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get current settings",
    description=(
        "Returns the current application configuration. Sensitive values "
        "are masked. Optionally filter by section (ai, analytics, workers, "
        "security, logging, storage)."
    ),
)
async def get_settings(
    section: str | None = Query(
        default=None,
        description="Optional section filter.",
    ),
    settings_service: Annotated[
        SettingsService, Depends(get_settings_service)
    ] = ...,
) -> Any:
    """Get current application settings.

    Args:
        section: Optional section to filter by.
        settings_service: Injected settings service.

    Returns:
        :class:`SettingsResponse` with configuration values.
    """
    return settings_service.get_settings(section=section)


@router.put(
    "",
    summary="Update settings",
    description=(
        "Updates one or more configuration settings at runtime. Only "
        "non-protected settings can be modified."
    ),
)
async def update_settings(
    payload: SettingsUpdate,
    settings_service: Annotated[
        SettingsService, Depends(get_settings_service)
    ] = ...,
) -> Any:
    """Update configuration settings.

    Converts the SettingsUpdate payload to a dictionary of key-value pairs
    excluding None values, then delegates to the service's bulk update.

    Args:
        payload: Settings update payload with optional fields.
        settings_service: Injected settings service.

    Returns:
        List of per-setting update results.
    """
    updates: dict[str, Any] = {
        key: value
        for key, value in payload.model_dump(exclude_none=True).items()
    }

    if not updates:
        return []

    return settings_service.update_settings_bulk(updates=updates)


@router.post(
    "/validate",
    summary="Validate a setting",
    description=(
        "Validates a proposed configuration value without applying it. "
        "Returns whether the value is valid and a human-readable message."
    ),
)
async def validate_setting(
    key: str = Query(description="Setting key to validate."),
    value: str = Query(description="Proposed value for the setting."),
    settings_service: Annotated[
        SettingsService, Depends(get_settings_service)
    ] = ...,
) -> Any:
    """Validate a configuration setting.

    Args:
        key: The setting key to validate.
        value: The proposed value.
        settings_service: Injected settings service.

    Returns:
        Validation result with validity flag and message.
    """
    return settings_service.validate_setting(key=key, value=value)


@router.post(
    "/reset",
    summary="Reset settings to defaults",
    description=(
        "Resets configuration settings to their default values. "
        "Optionally reset only a specific section."
    ),
)
async def reset_settings(
    section: str | None = Query(
        default=None,
        description="Optional section to reset.",
    ),
    settings_service: Annotated[
        SettingsService, Depends(get_settings_service)
    ] = ...,
) -> Any:
    """Reset settings to factory defaults.

    Args:
        section: Optional section to reset.
        settings_service: Injected settings service.

    Returns:
        Reset results with count of changed settings.
    """
    return settings_service.reset_to_defaults(section=section)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]
