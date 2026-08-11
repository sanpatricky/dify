from sqlalchemy.orm import Session, sessionmaker

from models.account import Account
from models.enums import TagType
from models.model import App, AppMode, Tag, TagBinding
from repositories.app_info_query_repository import AppInfoQueryRepository
from services.app_info_query_service import AppInfoRecord

_APP_ID = "11111111-1111-1111-1111-111111111111"
_TENANT_ID = "22222222-2222-2222-2222-222222222222"
_ACCOUNT_ID = "33333333-3333-3333-3333-333333333333"
_OTHER_TENANT_ID = "44444444-4444-4444-4444-444444444444"


def _persist_app(session: Session, *, mode: AppMode = AppMode.CHAT, created_by: str | None = _ACCOUNT_ID) -> App:
    app = App(
        id=_APP_ID,
        tenant_id=_TENANT_ID,
        name="Test App",
        description="A test application",
        mode=mode,
        icon_type=None,
        icon=None,
        icon_background=None,
        enable_site=True,
        enable_api=True,
        is_public=True,
        max_active_requests=None,
        created_by=created_by,
    )
    session.add(app)
    session.flush()
    return app


def test_get_info_returns_none_for_missing_app(sqlite_session_factory: sessionmaker[Session]) -> None:
    repository = AppInfoQueryRepository(session_factory=sqlite_session_factory)

    assert repository.get_info(_APP_ID) is None


def test_get_info_maps_app_mode_and_author(sqlite_session_factory: sessionmaker[Session]) -> None:
    with sqlite_session_factory.begin() as session:
        _persist_app(session, mode=AppMode.WORKFLOW)
        account = Account(name="Test Author", email="owner@example.com")
        account.id = _ACCOUNT_ID
        session.add(account)

    result = AppInfoQueryRepository(session_factory=sqlite_session_factory).get_info(_APP_ID)

    assert result == AppInfoRecord(
        name="Test App",
        description="A test application",
        tags=(),
        mode=AppMode.WORKFLOW.value,
        author_name="Test Author",
    )


def test_get_info_returns_only_tenant_scoped_app_tags(sqlite_session_factory: sessionmaker[Session]) -> None:
    with sqlite_session_factory.begin() as session:
        app = _persist_app(session)
        visible = Tag(tenant_id=_TENANT_ID, type=TagType.APP, name="visible", created_by=_ACCOUNT_ID)
        visible_second = Tag(
            tenant_id=_TENANT_ID,
            type=TagType.APP,
            name="visible-second",
            created_by=_ACCOUNT_ID,
        )
        foreign_tag = Tag(
            tenant_id=_OTHER_TENANT_ID,
            type=TagType.APP,
            name="foreign-tag",
            created_by=_ACCOUNT_ID,
        )
        foreign_binding = Tag(
            tenant_id=_TENANT_ID,
            type=TagType.APP,
            name="foreign-binding",
            created_by=_ACCOUNT_ID,
        )
        knowledge = Tag(
            tenant_id=_TENANT_ID,
            type=TagType.KNOWLEDGE,
            name="knowledge",
            created_by=_ACCOUNT_ID,
        )
        session.add_all([visible, visible_second, foreign_tag, foreign_binding, knowledge])
        session.flush()
        session.add_all(
            [
                TagBinding(
                    tenant_id=_TENANT_ID,
                    tag_id=visible.id,
                    target_id=app.id,
                    created_by=_ACCOUNT_ID,
                ),
                TagBinding(
                    tenant_id=_TENANT_ID,
                    tag_id=visible_second.id,
                    target_id=app.id,
                    created_by=_ACCOUNT_ID,
                ),
                TagBinding(
                    tenant_id=_TENANT_ID,
                    tag_id=foreign_tag.id,
                    target_id=app.id,
                    created_by=_ACCOUNT_ID,
                ),
                TagBinding(
                    tenant_id=_OTHER_TENANT_ID,
                    tag_id=foreign_binding.id,
                    target_id=app.id,
                    created_by=_ACCOUNT_ID,
                ),
                TagBinding(
                    tenant_id=_TENANT_ID,
                    tag_id=knowledge.id,
                    target_id=app.id,
                    created_by=_ACCOUNT_ID,
                ),
            ]
        )

    result = AppInfoQueryRepository(session_factory=sqlite_session_factory).get_info(_APP_ID)

    assert result is not None
    assert set(result.tags) == {"visible", "visible-second"}
    assert result.author_name is None
