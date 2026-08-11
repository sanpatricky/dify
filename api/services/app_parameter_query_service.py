"""Application service for reading published app parameters."""

from collections.abc import Mapping
from typing import Any, NamedTuple, Protocol

from core.app.app_config.common.parameters_mapping import AppParametersDict, get_parameters_from_feature_dict
from core.app.apps.agent_app.errors import AgentAppGeneratorError, AgentAppNotPublishedError


class AppParameterConfigRecord(NamedTuple):
    features_dict: Mapping[str, Any]
    user_input_form: list[dict[str, Any]]


class AppParameterQuery(Protocol):
    def get_published(self, app_id: str, *, public_runtime: bool = False) -> AppParameterConfigRecord | None: ...


class AppParameterUnavailableError(Exception):
    """Raised when an app has no published parameter configuration."""


class AppParameterNotPublishedError(AppParameterUnavailableError):
    """Raised when a public Agent App has not been published."""


class AppParameterQueryService:
    def __init__(self, *, parameters: AppParameterQuery) -> None:
        self._parameters = parameters

    def get_parameters(self, app_id: str) -> AppParametersDict:
        config = self._parameters.get_published(app_id)
        return self._map_parameters(config)

    def get_public_parameters(self, app_id: str) -> AppParametersDict:
        try:
            config = self._parameters.get_published(app_id, public_runtime=True)
        except AgentAppNotPublishedError:
            raise AppParameterNotPublishedError from None
        except AgentAppGeneratorError:
            raise AppParameterUnavailableError from None

        return self._map_parameters(config)

    @staticmethod
    def _map_parameters(config: AppParameterConfigRecord | None) -> AppParametersDict:
        if config is None:
            raise AppParameterUnavailableError

        return get_parameters_from_feature_dict(
            features_dict=config.features_dict,
            user_input_form=config.user_input_form,
        )
