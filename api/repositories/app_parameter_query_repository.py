"""Database repository for published app parameter configuration."""

from typing import Any, cast, override

from sqlalchemy.orm import Session, sessionmaker

from models.model import App, AppMode, load_annotation_reply_config
from services.app_parameter_query_service import AppParameterConfigRecord, AppParameterQuery


class AppParameterQueryRepository(AppParameterQuery):
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @override
    def get_published(self, app_id: str) -> AppParameterConfigRecord | None:
        with self._session_factory() as session:
            app = session.get(App, app_id)
            if app is None:
                return None

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
