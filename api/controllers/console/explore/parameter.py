from typing import Any

from pydantic import BaseModel, Field

from controllers.common import fields
from controllers.common.schema import register_response_schema_models
from controllers.console import console_ns
from controllers.console.app.error import AppUnavailableError
from controllers.console.explore.wraps import InstalledAppResource
from extensions.ext_application_services import application_services
from models.model import InstalledApp
from services.app_parameter_query_service import AppParameterUnavailableError


class ExploreAppMetaResponse(BaseModel):
    """Metadata consumed by the installed-app chat UI.

    Built-in tool icons are URL strings; API-based tool icons are provider-defined payload objects.
    """

    tool_icons: dict[str, str | dict[str, Any]] = Field(default_factory=dict)


register_response_schema_models(console_ns, fields.Parameters, ExploreAppMetaResponse)


@console_ns.route("/installed-apps/<uuid:installed_app_id>/parameters", endpoint="installed_app_parameters")
class AppParameterApi(InstalledAppResource):
    """Resource for app variables."""

    @console_ns.response(200, "Success", console_ns.models[fields.Parameters.__name__])
    def get(self, installed_app: InstalledApp):
        """Retrieve app parameters."""
        try:
            parameters = application_services().app_parameter_queries.get_parameters(installed_app.app_id)
        except AppParameterUnavailableError:
            raise AppUnavailableError() from None

        return fields.Parameters.model_validate(parameters).model_dump(mode="json")


@console_ns.route("/installed-apps/<uuid:installed_app_id>/meta", endpoint="installed_app_meta")
class ExploreAppMetaApi(InstalledAppResource):
    @console_ns.response(200, "Success", console_ns.models[ExploreAppMetaResponse.__name__])
    def get(self, installed_app: InstalledApp):
        """Get app meta"""
        return application_services().app_meta_queries.get_meta(installed_app.app_id)
