"""Unit tests for controllers.web.app endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from controllers.web.app import AppAccessMode, AppMeta, AppParameterApi, AppWebAuthPermission
from controllers.web.error import AgentNotPublishedError, AppUnavailableError
from core.app.app_config.common.parameters_mapping import get_parameters_from_feature_dict
from enums.webapp_access_mode import WebAppAccessMode
from services.app_parameter_query_service import AppParameterNotPublishedError, AppParameterUnavailableError


# ---------------------------------------------------------------------------
# AppParameterApi
# ---------------------------------------------------------------------------
class TestAppParameterApi:
    @patch("controllers.web.app.application_services")
    def test_get_returns_public_parameters(self, application_services: MagicMock, app: Flask) -> None:
        parameter_queries = MagicMock()
        parameter_queries.get_public_parameters.return_value = get_parameters_from_feature_dict(
            features_dict={"opening_statement": "Hello"},
            user_input_form=[],
        )
        application_services.return_value = SimpleNamespace(app_parameter_queries=parameter_queries)
        app_model = SimpleNamespace(id="app-1")

        with app.test_request_context("/parameters"):
            result = AppParameterApi().get(app_model, SimpleNamespace())

        assert result["opening_statement"] == "Hello"
        parameter_queries.get_public_parameters.assert_called_once_with("app-1")

    @pytest.mark.parametrize(
        ("service_error", "http_error"),
        [
            pytest.param(AppParameterNotPublishedError(), AgentNotPublishedError, id="not-published"),
            pytest.param(AppParameterUnavailableError(), AppUnavailableError, id="unavailable"),
        ],
    )
    @patch("controllers.web.app.application_services")
    def test_get_maps_query_errors(
        self,
        application_services: MagicMock,
        service_error: Exception,
        http_error: type[Exception],
        app: Flask,
    ) -> None:
        parameter_queries = MagicMock()
        parameter_queries.get_public_parameters.side_effect = service_error
        application_services.return_value = SimpleNamespace(app_parameter_queries=parameter_queries)

        with app.test_request_context("/parameters"):
            with pytest.raises(http_error):
                AppParameterApi().get(SimpleNamespace(id="app-1"), SimpleNamespace())


# ---------------------------------------------------------------------------
# AppMeta
# ---------------------------------------------------------------------------
class TestAppMeta:
    @patch("controllers.web.app.application_services")
    def test_get_returns_meta(self, application_services: MagicMock, app: Flask) -> None:
        meta_queries = MagicMock()
        meta_queries.get_meta.return_value = {"tool_icons": {}}
        application_services.return_value = SimpleNamespace(app_meta_queries=meta_queries)
        app_model = SimpleNamespace(id="app-1")

        with app.test_request_context("/meta"):
            result = AppMeta().get(app_model, SimpleNamespace())

        assert result == {"tool_icons": {}}
        meta_queries.get_meta.assert_called_once_with("app-1")


# ---------------------------------------------------------------------------
# AppAccessMode
# ---------------------------------------------------------------------------
class TestAppAccessMode:
    @patch("controllers.web.app.application_services")
    def test_delegates_validated_app_references(self, application_services: MagicMock, app: Flask) -> None:
        access_mode_queries = MagicMock()
        access_mode_queries.get_access_mode.return_value = WebAppAccessMode.SSO_VERIFIED
        application_services.return_value = SimpleNamespace(webapp_access_mode_queries=access_mode_queries)

        with app.test_request_context("/webapp/access-mode?appId=app-1&appCode=code-1"):
            result = AppAccessMode().get()

        assert result == {"accessMode": "sso_verified"}
        access_mode_queries.get_access_mode.assert_called_once_with(app_id="app-1", app_code="code-1")


# ---------------------------------------------------------------------------
# AppWebAuthPermission
# ---------------------------------------------------------------------------
class TestAppWebAuthPermission:
    @patch("controllers.web.app.WebAppAuthService.is_app_require_permission_check", return_value=False)
    def test_returns_true_when_no_permission_check_required(self, mock_check: MagicMock, app: Flask) -> None:
        with app.test_request_context("/webapp/permission?appId=app-1", headers={"X-App-Code": "code1"}):
            result = AppWebAuthPermission().get()

        assert result == {"result": True}

    def test_raises_when_missing_app_id(self, app: Flask) -> None:
        with app.test_request_context("/webapp/permission", headers={"X-App-Code": "code1"}):
            with pytest.raises(ValueError, match="appId"):
                AppWebAuthPermission().get()
