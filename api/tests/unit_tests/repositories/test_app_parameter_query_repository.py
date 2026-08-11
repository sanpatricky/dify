import json

import pytest
from sqlalchemy.orm import Session, sessionmaker

from models.model import App, AppMode, AppModelConfig
from models.workflow import Workflow, WorkflowKind, WorkflowType
from repositories.app_parameter_query_repository import AppParameterQueryRepository
from services.app_parameter_query_service import AppParameterConfigRecord

_APP_ID = "11111111-1111-1111-1111-111111111111"
_TENANT_ID = "22222222-2222-2222-2222-222222222222"
_ACCOUNT_ID = "33333333-3333-3333-3333-333333333333"


def _persist_app(session: Session, *, mode: AppMode = AppMode.CHAT) -> App:
    app = App(
        id=_APP_ID,
        tenant_id=_TENANT_ID,
        name="Parameter app",
        description="",
        mode=mode,
        icon_type=None,
        icon=None,
        icon_background=None,
        enable_site=True,
        enable_api=True,
        is_public=True,
        max_active_requests=None,
    )
    session.add(app)
    session.flush()
    return app


def test_get_published_returns_none_for_missing_app(sqlite_session_factory: sessionmaker[Session]) -> None:
    repository = AppParameterQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_published(_APP_ID) is None


@pytest.mark.parametrize(
    ("mode", "workflow_type"),
    [
        pytest.param(AppMode.WORKFLOW, WorkflowType.WORKFLOW, id="workflow"),
        pytest.param(AppMode.ADVANCED_CHAT, WorkflowType.CHAT, id="advanced-chat"),
    ],
)
def test_get_published_returns_workflow_features_and_legacy_input_form(
    sqlite_session_factory: sessionmaker[Session],
    mode: AppMode,
    workflow_type: WorkflowType,
) -> None:
    variable = {
        "variable": "query",
        "label": "Query",
        "type": "text-input",
        "required": True,
        "max_length": 48,
    }
    with sqlite_session_factory() as session:
        app = _persist_app(session, mode=mode)
        workflow = Workflow(
            id="44444444-4444-4444-4444-444444444444",
            tenant_id=_TENANT_ID,
            app_id=app.id,
            type=workflow_type,
            kind=WorkflowKind.STANDARD,
            version="1",
            graph=json.dumps({"nodes": [{"id": "start", "data": {"type": "start", "variables": [variable]}}]}),
            features=json.dumps({"opening_statement": "Hello from workflow"}),
            created_by=_ACCOUNT_ID,
            environment_variables=[],
            conversation_variables=[],
            rag_pipeline_variables=[],
        )
        session.add(workflow)
        app.workflow_id = workflow.id
        session.commit()

    result = AppParameterQueryRepository(session_factory=sqlite_session_factory).get_published(_APP_ID)

    assert result == AppParameterConfigRecord(
        features_dict={"opening_statement": "Hello from workflow"},
        user_input_form=[{"text-input": variable}],
    )


def test_get_published_returns_none_for_workflow_without_published_workflow(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        _persist_app(session, mode=AppMode.WORKFLOW)
        session.commit()

    repository = AppParameterQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_published(_APP_ID) is None


def test_get_published_returns_model_config_and_annotation_projection(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    user_input_form = [{"paragraph": {"variable": "details", "label": "Details", "required": False}}]
    with sqlite_session_factory() as session:
        app = _persist_app(session)
        app_model_config = AppModelConfig(
            app_id=app.id,
            opening_statement="Hello from model config",
            user_input_form=json.dumps(user_input_form),
        )
        session.add(app_model_config)
        session.flush()
        app.app_model_config_id = app_model_config.id
        session.commit()

    result = AppParameterQueryRepository(session_factory=sqlite_session_factory).get_published(_APP_ID)

    assert result is not None
    assert result.features_dict["opening_statement"] == "Hello from model config"
    assert result.features_dict["annotation_reply"] == {"enabled": False}
    assert result.user_input_form == user_input_form


def test_get_published_returns_none_for_app_without_published_model_config(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        _persist_app(session)
        session.commit()

    repository = AppParameterQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_published(_APP_ID) is None


def test_get_published_preserves_legacy_agent_model_config(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        app = _persist_app(session, mode=AppMode.AGENT)
        app_model_config = AppModelConfig(app_id=app.id, opening_statement="Legacy Agent config")
        session.add(app_model_config)
        session.flush()
        app.app_model_config_id = app_model_config.id
        session.commit()

    result = AppParameterQueryRepository(session_factory=sqlite_session_factory).get_published(_APP_ID)

    assert result is not None
    assert result.features_dict["opening_statement"] == "Legacy Agent config"


def test_get_published_public_reuses_standard_projection(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        app = _persist_app(session)
        app_model_config = AppModelConfig(app_id=app.id, opening_statement="Public config")
        session.add(app_model_config)
        session.flush()
        app.app_model_config_id = app_model_config.id
        session.commit()

    result = AppParameterQueryRepository(session_factory=sqlite_session_factory).get_published(
        _APP_ID, public_runtime=True
    )

    assert result is not None
    assert result.features_dict["opening_statement"] == "Public config"
