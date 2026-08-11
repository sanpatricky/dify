import json

import pytest
from sqlalchemy.orm import Session, sessionmaker

from core.tools.entities.tool_entities import ApiProviderSchemaType
from models.model import App, AppMode, AppModelConfig
from models.tools import ApiToolProvider
from models.workflow import Workflow, WorkflowKind, WorkflowType
from repositories.app_meta_query_repository import AppMetaQueryRepository
from services.app_meta_query_service import AppMetaToolRecord

_APP_ID = "11111111-1111-1111-1111-111111111111"
_TENANT_ID = "22222222-2222-2222-2222-222222222222"
_ACCOUNT_ID = "33333333-3333-3333-3333-333333333333"
_WORKFLOW_ID = "44444444-4444-4444-4444-444444444444"
_PROVIDER_ID = "55555555-5555-5555-5555-555555555555"
_MISSING_PROVIDER_ID = "66666666-6666-6666-6666-666666666666"


def _persist_app(session: Session, *, mode: AppMode = AppMode.CHAT) -> App:
    app = App(
        id=_APP_ID,
        tenant_id=_TENANT_ID,
        name="Meta app",
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


def _tool(provider_type: str, provider_id: str, tool_name: str) -> dict[str, object]:
    return {
        "provider_type": provider_type,
        "provider_id": provider_id,
        "tool_name": tool_name,
        "tool_parameters": {},
    }


def test_get_tool_icon_sources_returns_none_for_missing_app(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    repository = AppMetaQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_tool_icon_sources(_APP_ID) is None


@pytest.mark.parametrize(
    ("mode", "workflow_type"),
    [
        pytest.param(AppMode.WORKFLOW, WorkflowType.WORKFLOW, id="workflow"),
        pytest.param(AppMode.ADVANCED_CHAT, WorkflowType.CHAT, id="advanced-chat"),
    ],
)
def test_get_tool_icon_sources_reads_workflow_tools(
    sqlite_session_factory: sessionmaker[Session],
    mode: AppMode,
    workflow_type: WorkflowType,
) -> None:
    with sqlite_session_factory() as session:
        app = _persist_app(session, mode=mode)
        workflow = Workflow(
            id=_WORKFLOW_ID,
            tenant_id=_TENANT_ID,
            app_id=app.id,
            type=workflow_type,
            kind=WorkflowKind.STANDARD,
            version="1",
            graph=json.dumps(
                {
                    "nodes": [
                        {"id": "start", "data": {"type": "start"}},
                        {"id": "tool", "data": {"type": "tool", **_tool("builtin", "search", "search")}},
                    ]
                }
            ),
            features="{}",
            created_by=_ACCOUNT_ID,
            environment_variables=[],
            conversation_variables=[],
            rag_pipeline_variables=[],
        )
        session.add(workflow)
        app.workflow_id = workflow.id
        session.commit()

    result = AppMetaQueryRepository(session_factory=sqlite_session_factory).get_tool_icon_sources(_APP_ID)

    assert result == (AppMetaToolRecord("builtin", "search", "search", None),)


def test_get_tool_icon_sources_reads_model_config_and_api_provider_icons(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        app = _persist_app(session)
        tools = [
            _tool("builtin", "search", "search"),
            _tool("api", _PROVIDER_ID, "weather"),
            _tool("api", _MISSING_PROVIDER_ID, "missing"),
            _tool("workflow", "workflow-provider", "workflow-tool"),
            {"provider_type": "builtin", "provider_id": "legacy", "tool_name": "legacy"},
        ]
        app_model_config = AppModelConfig(
            app_id=app.id,
            agent_mode=json.dumps({"enabled": True, "strategy": "react", "tools": tools, "prompt": None}),
        )
        provider = ApiToolProvider(
            name="Weather",
            icon='{"background":"#fff","content":"W"}',
            schema="{}",
            schema_type_str=ApiProviderSchemaType.OPENAPI,
            user_id=_ACCOUNT_ID,
            tenant_id=_TENANT_ID,
            description="",
            tools_str="[]",
            credentials_str="{}",
        )
        provider.id = _PROVIDER_ID
        session.add_all([app_model_config, provider])
        session.flush()
        app.app_model_config_id = app_model_config.id
        session.commit()

    result = AppMetaQueryRepository(session_factory=sqlite_session_factory).get_tool_icon_sources(_APP_ID)

    assert result == (
        AppMetaToolRecord("builtin", "search", "search", None),
        AppMetaToolRecord("api", _PROVIDER_ID, "weather", '{"background":"#fff","content":"W"}'),
        AppMetaToolRecord("api", _MISSING_PROVIDER_ID, "missing", None),
        AppMetaToolRecord("workflow", "workflow-provider", "workflow-tool", None),
    )


@pytest.mark.parametrize("mode", [AppMode.CHAT, AppMode.WORKFLOW])
def test_get_tool_icon_sources_returns_empty_for_missing_published_config(
    sqlite_session_factory: sessionmaker[Session],
    mode: AppMode,
) -> None:
    with sqlite_session_factory() as session:
        _persist_app(session, mode=mode)
        session.commit()

    repository = AppMetaQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_tool_icon_sources(_APP_ID) == ()
