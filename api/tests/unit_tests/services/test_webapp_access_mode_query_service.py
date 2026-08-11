from unittest.mock import MagicMock, create_autospec

import pytest

from enums.webapp_access_mode import WebAppAccessMode
from services.webapp_access_mode_query_service import AppCodeQuery, WebAppAccessModeQueryService


def _service(
    *,
    app_codes: MagicMock,
    enabled: bool = True,
    access_mode: WebAppAccessMode = WebAppAccessMode.PRIVATE,
) -> tuple[WebAppAccessModeQueryService, MagicMock]:
    access_mode_for_app = MagicMock(return_value=access_mode)
    return (
        WebAppAccessModeQueryService(
            app_codes=app_codes,
            webapp_auth_enabled=enabled,
            access_mode_for_app=access_mode_for_app,
        ),
        access_mode_for_app,
    )


def test_disabled_auth_returns_public_before_resolving_app() -> None:
    app_codes: MagicMock = create_autospec(AppCodeQuery, instance=True, spec_set=True)
    service, access_mode_for_app = _service(app_codes=app_codes, enabled=False)

    assert service.get_access_mode(app_id=None, app_code=None) is WebAppAccessMode.PUBLIC
    app_codes.find_app_id.assert_not_called()
    access_mode_for_app.assert_not_called()


def test_enabled_auth_reads_access_mode_by_app_id() -> None:
    app_codes: MagicMock = create_autospec(AppCodeQuery, instance=True, spec_set=True)
    service, access_mode_for_app = _service(app_codes=app_codes, access_mode=WebAppAccessMode.PRIVATE)

    assert service.get_access_mode(app_id="app-1", app_code=None) is WebAppAccessMode.PRIVATE
    app_codes.find_app_id.assert_not_called()
    access_mode_for_app.assert_called_once_with("app-1")


def test_app_code_takes_precedence_over_app_id() -> None:
    app_codes: MagicMock = create_autospec(AppCodeQuery, instance=True, spec_set=True)
    app_codes.find_app_id.return_value = "resolved-id"
    service, access_mode_for_app = _service(app_codes=app_codes, access_mode=WebAppAccessMode.SSO_VERIFIED)

    assert service.get_access_mode(app_id="ignored-id", app_code="code-1") is WebAppAccessMode.SSO_VERIFIED
    app_codes.find_app_id.assert_called_once_with("code-1")
    access_mode_for_app.assert_called_once_with("resolved-id")


def test_missing_app_code_uses_existing_error_contract() -> None:
    app_codes: MagicMock = create_autospec(AppCodeQuery, instance=True, spec_set=True)
    app_codes.find_app_id.return_value = None
    service, access_mode_for_app = _service(app_codes=app_codes)

    with pytest.raises(ValueError, match="^App with code missing-code not found$"):
        service.get_access_mode(app_id="must-not-fallback", app_code="missing-code")

    access_mode_for_app.assert_not_called()


def test_enabled_auth_requires_app_id_or_code() -> None:
    app_codes: MagicMock = create_autospec(AppCodeQuery, instance=True, spec_set=True)
    service, access_mode_for_app = _service(app_codes=app_codes)

    with pytest.raises(ValueError, match="^appId or appCode must be provided$"):
        service.get_access_mode(app_id=None, app_code=None)

    access_mode_for_app.assert_not_called()
