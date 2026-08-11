from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec, patch

import pytest

import controllers.console.explore.parameter as module
from controllers.console.app.error import AppUnavailableError
from services.app_meta_query_service import AppMetaQueryService
from services.app_parameter_query_service import AppParameterQueryService, AppParameterUnavailableError


def _installed_app() -> MagicMock:
    return MagicMock(app_id="app-1")


def _application_services() -> tuple[SimpleNamespace, MagicMock, MagicMock]:
    meta_queries: MagicMock = create_autospec(AppMetaQueryService, instance=True, spec_set=True)
    parameter_queries: MagicMock = create_autospec(AppParameterQueryService, instance=True, spec_set=True)
    return (
        SimpleNamespace(app_meta_queries=meta_queries, app_parameter_queries=parameter_queries),
        meta_queries,
        parameter_queries,
    )


class TestAppParameterApi:
    def test_get_parameters(self) -> None:
        services, _, parameter_queries = _application_services()
        parameter_queries.get_parameters.return_value = {"any": "thing"}
        validated = MagicMock()
        validated.model_dump.return_value = {"ok": True}
        installed_app = _installed_app()

        with (
            patch.object(module, "application_services", return_value=services),
            patch.object(module.fields.Parameters, "model_validate", return_value=validated) as validate_parameters,
        ):
            result = unwrap(module.AppParameterApi.get)(module.AppParameterApi(), installed_app)

        assert result == {"ok": True}
        parameter_queries.get_parameters.assert_called_once_with("app-1")
        validate_parameters.assert_called_once_with({"any": "thing"})
        validated.model_dump.assert_called_once_with(mode="json")

    def test_get_maps_unavailable_parameter_config_to_app_unavailable(self) -> None:
        services, _, parameter_queries = _application_services()
        parameter_queries.get_parameters.side_effect = AppParameterUnavailableError

        with (
            patch.object(module, "application_services", return_value=services),
            pytest.raises(AppUnavailableError),
        ):
            unwrap(module.AppParameterApi.get)(module.AppParameterApi(), _installed_app())


class TestExploreAppMetaApi:
    def test_get_meta(self) -> None:
        services, meta_queries, _ = _application_services()
        meta_queries.get_meta.return_value = {"tool_icons": {"search": "/icon"}}
        installed_app = _installed_app()

        with patch.object(module, "application_services", return_value=services):
            result = unwrap(module.ExploreAppMetaApi.get)(module.ExploreAppMetaApi(), installed_app)

        assert result == {"tool_icons": {"search": "/icon"}}
        meta_queries.get_meta.assert_called_once_with("app-1")
