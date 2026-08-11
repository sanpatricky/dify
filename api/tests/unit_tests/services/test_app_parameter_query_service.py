from unittest.mock import create_autospec, patch

import pytest

import services.app_parameter_query_service as module
from core.app.apps.agent_app.errors import AgentAppGeneratorError, AgentAppNotPublishedError
from services.app_parameter_query_service import (
    AppParameterConfigRecord,
    AppParameterNotPublishedError,
    AppParameterQuery,
    AppParameterQueryService,
    AppParameterUnavailableError,
)


def test_get_parameters_maps_published_config() -> None:
    parameters = create_autospec(AppParameterQuery, instance=True, spec_set=True)
    record = AppParameterConfigRecord(
        features_dict={"opening_statement": "Hello"},
        user_input_form=[{"text-input": {"variable": "query"}}],
    )
    parameters.get_published.return_value = record
    mapped = {"mapped": True}

    with patch.object(module, "get_parameters_from_feature_dict", return_value=mapped) as map_parameters:
        result = AppParameterQueryService(parameters=parameters).get_parameters("app-1")

    assert result is mapped
    parameters.get_published.assert_called_once_with("app-1")
    map_parameters.assert_called_once_with(
        features_dict=record.features_dict,
        user_input_form=record.user_input_form,
    )


def test_get_parameters_rejects_missing_published_config() -> None:
    parameters = create_autospec(AppParameterQuery, instance=True, spec_set=True)
    parameters.get_published.return_value = None

    with pytest.raises(AppParameterUnavailableError):
        AppParameterQueryService(parameters=parameters).get_parameters("app-1")


def test_get_public_parameters_maps_public_config() -> None:
    parameters = create_autospec(AppParameterQuery, instance=True, spec_set=True)
    record = AppParameterConfigRecord(
        features_dict={"opening_statement": "Hello"},
        user_input_form=[{"text-input": {"variable": "query"}}],
    )
    parameters.get_published.return_value = record
    mapped = {"mapped": True}

    with patch.object(module, "get_parameters_from_feature_dict", return_value=mapped):
        result = AppParameterQueryService(parameters=parameters).get_public_parameters("app-1")

    assert result is mapped
    parameters.get_published.assert_called_once_with("app-1", public_runtime=True)


def test_get_public_parameters_rejects_missing_config() -> None:
    parameters = create_autospec(AppParameterQuery, instance=True, spec_set=True)
    parameters.get_published.return_value = None

    with pytest.raises(AppParameterUnavailableError):
        AppParameterQueryService(parameters=parameters).get_public_parameters("app-1")


@pytest.mark.parametrize(
    ("source_error", "expected_error"),
    [
        pytest.param(AgentAppNotPublishedError("not published"), AppParameterNotPublishedError, id="not-published"),
        pytest.param(AgentAppGeneratorError("unavailable"), AppParameterUnavailableError, id="unavailable"),
    ],
)
def test_get_public_parameters_maps_agent_errors(source_error: Exception, expected_error: type[Exception]) -> None:
    parameters = create_autospec(AppParameterQuery, instance=True, spec_set=True)
    parameters.get_published.side_effect = source_error

    with pytest.raises(expected_error):
        AppParameterQueryService(parameters=parameters).get_public_parameters("app-1")
