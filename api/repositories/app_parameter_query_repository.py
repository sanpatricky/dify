"""Database repository for published app parameter configuration."""

from typing import Any, cast, override

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from core.agent.publish_visibility import agent_has_workflow_callable_active_snapshot
from core.app.apps.agent_app.app_feature_projection import merge_agent_app_features
from core.app.apps.agent_app.app_variable_projection import agent_app_variables_to_user_input_form
from core.app.apps.agent_app.errors import AgentAppGeneratorError, AgentAppNotPublishedError
from models.agent import AgentConfigSnapshot
from models.agent_config_entities import AgentSoulConfig
from models.model import App, AppMode, load_annotation_reply_config
from services.app_parameter_query_service import AppParameterConfigRecord, AppParameterQuery


def _get_public_agent_config(app: App, *, session: Session) -> AppParameterConfigRecord:
    app_model_config = app.app_model_config_with_session(session=session)
    agent = app.agent_app_binding_with_session(session=session)
    if agent is None:
        raise AgentAppGeneratorError("Agent App has no bound Agent")
    if not agent_has_workflow_callable_active_snapshot(session=session, agent=agent):
        raise AgentAppNotPublishedError("Agent has not been published")

    snapshot = session.scalar(
        select(AgentConfigSnapshot)
        .where(
            AgentConfigSnapshot.tenant_id == app.tenant_id,
            AgentConfigSnapshot.agent_id == agent.id,
            AgentConfigSnapshot.id == agent.active_config_snapshot_id,
        )
        .limit(1)
    )
    if snapshot is None:
        raise AgentAppGeneratorError("Agent published version not found")

    agent_soul = AgentSoulConfig.model_validate(snapshot.config_snapshot_dict)
    annotation_reply = load_annotation_reply_config(session, app.id) if app_model_config else None
    return AppParameterConfigRecord(
        features_dict=merge_agent_app_features(
            agent_soul=agent_soul,
            app_model_config=app_model_config,
            annotation_reply=annotation_reply,
        ),
        user_input_form=agent_app_variables_to_user_input_form(agent_soul.app_variables),
    )


class AppParameterQueryRepository(AppParameterQuery):
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @override
    def get_published(self, app_id: str, *, public_runtime: bool = False) -> AppParameterConfigRecord | None:
        with self._session_factory() as session:
            app = session.get(App, app_id)
            if app is None:
                return None

            if public_runtime and app.mode == AppMode.AGENT:
                return _get_public_agent_config(app, session=session)

            if app.mode in {AppMode.ADVANCED_CHAT, AppMode.WORKFLOW}:
                workflow = app.workflow_with_session(session=session)
                if workflow is None:
                    return None

                return AppParameterConfigRecord(
                    features_dict=workflow.features_dict,
                    user_input_form=cast(list[dict[str, Any]], workflow.user_input_form(to_old_structure=True)),
                )

            app_model_config = app.app_model_config_with_session(session=session)
            if app_model_config is None:
                return None

            features_dict = app_model_config.to_dict(
                annotation_reply=load_annotation_reply_config(session, app.id),
            )
            return AppParameterConfigRecord(
                features_dict=features_dict,
                user_input_form=cast(list[dict[str, Any]], features_dict.get("user_input_form", [])),
            )
