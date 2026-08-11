"""Database repository for app tool metadata."""

from typing import Any, cast, override

from sqlalchemy.orm import Session, sessionmaker

from models.model import App, AppMode, AppModelConfig
from models.tools import ApiToolProvider
from models.workflow import Workflow
from services.app_meta_query_service import AppMetaQuery, AppMetaToolRecord


class AppMetaQueryRepository(AppMetaQuery):
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @override
    def get_tool_icon_sources(self, app_id: str) -> tuple[AppMetaToolRecord, ...] | None:
        with self._session_factory() as session:
            app = session.get(App, app_id)
            if app is None:
                return None

            records: list[AppMetaToolRecord] = []
            for tool in self._get_tools(session, app):
                if len(tool) < 4:
                    continue

                provider_type = str(tool.get("provider_type", ""))
                provider_id = str(tool.get("provider_id", ""))
                tool_name = str(tool.get("tool_name", ""))
                provider_icon: str | None = None
                if provider_type == "api":
                    try:
                        provider = session.get(ApiToolProvider, provider_id)
                        provider_icon = provider.icon if provider is not None else None
                    except Exception:
                        # Preserve the legacy response fallback when a provider cannot be loaded.
                        provider_icon = None

                records.append(
                    AppMetaToolRecord(
                        provider_type=provider_type,
                        provider_id=provider_id,
                        tool_name=tool_name,
                        provider_icon=provider_icon,
                    )
                )

            return tuple(records)

    @staticmethod
    def _get_tools(session: Session, app: App) -> list[dict[str, Any]]:
        if app.mode in {AppMode.ADVANCED_CHAT, AppMode.WORKFLOW}:
            workflow = session.get(Workflow, app.workflow_id) if app.workflow_id else None
            if workflow is None:
                return []

            tools: list[dict[str, Any]] = []
            nodes = cast(list[dict[str, Any]], workflow.graph_dict.get("nodes", []))
            for node in nodes:
                node_data = node.get("data", {})
                if node_data.get("type") == "tool":
                    tools.append(
                        {
                            "provider_type": node_data.get("provider_type"),
                            "provider_id": node_data.get("provider_id"),
                            "tool_name": node_data.get("tool_name"),
                            "tool_parameters": {},
                        }
                    )
            return tools

        app_model_config = session.get(AppModelConfig, app.app_model_config_id) if app.app_model_config_id else None
        if app_model_config is None:
            return []
        return cast(list[dict[str, Any]], app_model_config.agent_mode_dict.get("tools", []))
