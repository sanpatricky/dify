"""Application service for resolving web-app access modes."""

from collections.abc import Callable
from typing import Protocol

from enums.webapp_access_mode import WebAppAccessMode


class AppCodeQuery(Protocol):
    def find_app_id(self, app_code: str) -> str | None: ...


class WebAppAccessModeQueryService:
    def __init__(
        self,
        *,
        app_codes: AppCodeQuery,
        webapp_auth_enabled: bool,
        access_mode_for_app: Callable[[str], WebAppAccessMode],
    ) -> None:
        self._app_codes = app_codes
        self._webapp_auth_enabled = webapp_auth_enabled
        self._access_mode_for_app = access_mode_for_app

    def get_access_mode(self, *, app_id: str | None, app_code: str | None) -> WebAppAccessMode:
        if not self._webapp_auth_enabled:
            return WebAppAccessMode.PUBLIC

        if app_code:
            app_id = self._app_codes.find_app_id(app_code)
            if app_id is None:
                raise ValueError(f"App with code {app_code} not found")

        if not app_id:
            raise ValueError("appId or appCode must be provided")

        return self._access_mode_for_app(app_id)
