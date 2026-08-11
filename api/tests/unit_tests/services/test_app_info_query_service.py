from unittest.mock import MagicMock, create_autospec

import pytest

from services.app_info_query_service import AppInfoQuery, AppInfoQueryService, AppInfoRecord, AppInfoUnavailableError


def test_get_info_returns_repository_record() -> None:
    apps: MagicMock = create_autospec(AppInfoQuery, instance=True, spec_set=True)
    info = AppInfoRecord("Test App", "A test application", ("tag",), "chat", "Test Author")
    apps.get_info.return_value = info

    assert AppInfoQueryService(apps=apps).get_info("app-1") == info
    apps.get_info.assert_called_once_with("app-1")


def test_get_info_rejects_missing_app() -> None:
    apps = create_autospec(AppInfoQuery, instance=True, spec_set=True)
    apps.get_info.return_value = None

    with pytest.raises(AppInfoUnavailableError):
        AppInfoQueryService(apps=apps).get_info("missing")
