"""Application service for reading published app parameters."""

from collections.abc import Mapping
from typing import Any, NamedTuple, Protocol

from core.app.app_config.common.parameters_mapping import AppParametersDict, get_parameters_from_feature_dict


class AppParameterConfigRecord(NamedTuple):
    features_dict: Mapping[str, Any]
    user_input_form: list[dict[str, Any]]


class AppParameterQuery(Protocol):
    def get_published(self, app_id: str) -> AppParameterConfigRecord | None: ...


class AppParameterUnavailableError(Exception):
    """Raised when an app has no published parameter configuration."""


class AppParameterQueryService:
    def __init__(self, *, parameters: AppParameterQuery) -> None:
        self._parameters = parameters

    def get_parameters(self, app_id: str) -> AppParametersDict:
        config = self._parameters.get_published(app_id)
        if config is None:
            raise AppParameterUnavailableError

        return get_parameters_from_feature_dict(
            features_dict=config.features_dict,
            user_input_form=config.user_input_form,
        )
