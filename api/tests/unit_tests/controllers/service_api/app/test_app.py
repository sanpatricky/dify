"""SQLite-backed tests for Service API application controllers.

The authentication decorator resolves the app, tenant, and tenant owner before
the controller delegates each use case to its application query service.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from flask import Flask
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from werkzeug.exceptions import Forbidden, Unauthorized

from controllers.service_api.app import app as app_controller
from controllers.service_api.app.app import AppInfoApi, AppMetaApi, AppParameterApi
from controllers.service_api.app.error import AgentNotPublishedError, AppUnavailableError
from core.app.app_config.common.parameters_mapping import get_parameters_from_feature_dict
from models.account import Account, Tenant, TenantAccountJoin, TenantAccountRole, TenantStatus
from models.base import TypeBase
from models.model import App, AppMode
from services.app_info_query_service import AppInfoRecord, AppInfoUnavailableError
from services.app_parameter_query_service import AppParameterNotPublishedError, AppParameterUnavailableError


@dataclass(frozen=True)
class _DatabaseBinding:
    session: scoped_session[Session]


@dataclass(frozen=True)
class _Token:
    app_id: str
    tenant_id: str


@dataclass(frozen=True)
class AppDatabase:
    """Persisted admission state used by the decorated controller methods."""

    session_maker: sessionmaker[Session]
    tenant_id: str
    app_id: str

    def update_app(self, **values: object) -> None:
        with self.session_maker.begin() as session:
            app = session.get_one(App, self.app_id)
            for key, value in values.items():
                setattr(app, key, value)

    def update_tenant(self, **values: object) -> None:
        with self.session_maker.begin() as session:
            tenant = session.get_one(Tenant, self.tenant_id)
            for key, value in values.items():
                setattr(tenant, key, value)

    def delete_row(self, model: type[object], object_id: str) -> None:
        table = model.__table__  # type: ignore[attr-defined]
        with self.session_maker.begin() as session:
            session.execute(table.delete().where(table.c.id == object_id))


@pytest.fixture
def flask_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def app_db(sqlite_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[AppDatabase]:
    """Create the minimal admission schema and bind every DB reference explicitly."""

    tables = [
        Tenant.__table__,
        Account.__table__,
        TenantAccountJoin.__table__,
        App.__table__,
    ]
    TypeBase.metadata.create_all(sqlite_engine, tables=tables)
    maker = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    registry = scoped_session(maker)
    binding = _DatabaseBinding(session=registry)
    monkeypatch.setattr("controllers.service_api.wraps.db", binding)

    tenant_id = str(uuid4())
    app_id = str(uuid4())
    owner_id = str(uuid4())
    with maker.begin() as session:
        tenant = Tenant(name="Visible tenant")
        tenant.id = tenant_id
        owner = Account(name="Test Author", email="owner@example.com")
        owner.id = owner_id
        app = App(
            id=app_id,
            tenant_id=tenant_id,
            name="Test App",
            description="A test application",
            mode=AppMode.CHAT,
            icon_type=None,
            icon=None,
            icon_background=None,
            enable_site=True,
            enable_api=True,
            max_active_requests=None,
            created_by=owner_id,
        )
        session.add_all([tenant, owner, app])
        session.flush()
        session.add(
            TenantAccountJoin(
                tenant_id=tenant_id,
                account_id=owner_id,
                current=True,
                role=TenantAccountRole.OWNER,
            )
        )

    database = AppDatabase(
        session_maker=maker,
        tenant_id=tenant_id,
        app_id=app_id,
    )
    try:
        yield database
    finally:
        registry.remove()


@pytest.fixture
def authenticated_controller(app_db: AppDatabase, monkeypatch: pytest.MonkeyPatch) -> Iterator[AppDatabase]:
    """Patch only token validation and Flask login signaling around real ORM auth."""

    monkeypatch.setattr(
        "controllers.service_api.wraps.validate_and_get_api_token",
        Mock(return_value=_Token(app_id=app_db.app_id, tenant_id=app_db.tenant_id)),
    )
    current_app = Mock()
    current_app.login_manager = Mock()
    current_app._get_current_object.return_value = Mock()
    monkeypatch.setattr("controllers.service_api.wraps.current_app", current_app)
    monkeypatch.setattr("controllers.service_api.wraps.user_logged_in", Mock())
    return app_db


def test_get_parameters_queries_authenticated_app(
    flask_app: Flask, authenticated_controller: AppDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    parameter_queries = Mock()
    parameter_queries.get_public_parameters.return_value = get_parameters_from_feature_dict(
        features_dict={"opening_statement": "Hello"},
        user_input_form=[],
    )
    monkeypatch.setattr(
        app_controller,
        "application_services",
        Mock(return_value=SimpleNamespace(app_parameter_queries=parameter_queries)),
    )

    with flask_app.test_request_context("/parameters", headers={"Authorization": "Bearer token"}):
        response = AppParameterApi().get()

    parameter_queries.get_public_parameters.assert_called_once_with(authenticated_controller.app_id)
    assert response["opening_statement"] == "Hello"


@pytest.mark.parametrize(
    ("service_error", "http_error"),
    [
        pytest.param(AppParameterNotPublishedError(), AgentNotPublishedError, id="not-published"),
        pytest.param(AppParameterUnavailableError(), AppUnavailableError, id="unavailable"),
    ],
)
@pytest.mark.usefixtures("authenticated_controller")
def test_get_parameters_maps_query_errors(
    flask_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    service_error: Exception,
    http_error: type[Exception],
) -> None:
    parameter_queries = Mock()
    parameter_queries.get_public_parameters.side_effect = service_error
    monkeypatch.setattr(
        app_controller,
        "application_services",
        Mock(return_value=SimpleNamespace(app_parameter_queries=parameter_queries)),
    )

    with flask_app.test_request_context("/parameters", headers={"Authorization": "Bearer token"}):
        with pytest.raises(http_error):
            AppParameterApi().get()


def test_get_meta_queries_authenticated_app(
    flask_app: Flask, authenticated_controller: AppDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    meta_queries = Mock()
    meta_queries.get_meta.return_value = {"tool_icons": {}}
    monkeypatch.setattr(
        app_controller,
        "application_services",
        Mock(return_value=SimpleNamespace(app_meta_queries=meta_queries)),
    )

    with flask_app.test_request_context("/meta", headers={"Authorization": "Bearer token"}):
        response = AppMetaApi().get()

    meta_queries.get_meta.assert_called_once_with(authenticated_controller.app_id)
    assert response == {"tool_icons": {}}


def test_get_info_queries_authenticated_app(
    flask_app: Flask,
    authenticated_controller: AppDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_info_queries = Mock()
    app_info_queries.get_info.return_value = AppInfoRecord(
        name="Test App",
        description="A test application",
        tags=("test-tag",),
        mode="chat",
        author_name="Test Author",
    )
    monkeypatch.setattr(
        app_controller,
        "application_services",
        Mock(return_value=SimpleNamespace(app_info_queries=app_info_queries)),
    )

    with flask_app.test_request_context("/info", headers={"Authorization": "Bearer token"}):
        response = AppInfoApi().get()

    app_info_queries.get_info.assert_called_once_with(authenticated_controller.app_id)
    assert response == {
        "name": "Test App",
        "description": "A test application",
        "tags": ["test-tag"],
        "mode": "chat",
        "author_name": "Test Author",
    }


@pytest.mark.usefixtures("authenticated_controller")
def test_get_info_maps_unavailable_app(flask_app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    app_info_queries = Mock()
    app_info_queries.get_info.side_effect = AppInfoUnavailableError
    monkeypatch.setattr(
        app_controller,
        "application_services",
        Mock(return_value=SimpleNamespace(app_info_queries=app_info_queries)),
    )

    with flask_app.test_request_context("/info", headers={"Authorization": "Bearer token"}):
        with pytest.raises(AppUnavailableError):
            AppInfoApi().get()


@pytest.mark.parametrize("state", ["missing", "disabled", "archived", "ownerless"])
def test_authentication_rejects_empty_or_invisible_database_state(
    flask_app: Flask,
    authenticated_controller: AppDatabase,
    state: str,
) -> None:
    expected_error: type[Exception] = Forbidden
    if state == "missing":
        authenticated_controller.delete_row(App, authenticated_controller.app_id)
    elif state == "disabled":
        authenticated_controller.update_app(enable_api=False)
    elif state == "archived":
        authenticated_controller.update_tenant(status=TenantStatus.ARCHIVE)
    else:
        with authenticated_controller.session_maker.begin() as session:
            session.execute(TenantAccountJoin.__table__.delete())
        expected_error = Unauthorized

    with flask_app.test_request_context("/info", headers={"Authorization": "Bearer token"}):
        with pytest.raises(expected_error):
            AppInfoApi().get()
