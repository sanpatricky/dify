from sqlalchemy.orm import Session, sessionmaker

from models.model import Site
from repositories.app_code_query_repository import AppCodeQueryRepository

_APP_ID = "11111111-1111-1111-1111-111111111111"


def test_find_app_id_returns_matching_site_app(sqlite_session_factory: sessionmaker[Session]) -> None:
    with sqlite_session_factory.begin() as session:
        session.add(
            Site(
                app_id=_APP_ID,
                code="site-code",
                title="Test Site",
                default_language="en-US",
                customize_token_strategy="uuid",
            )
        )

    assert AppCodeQueryRepository(session_factory=sqlite_session_factory).find_app_id("site-code") == _APP_ID


def test_find_app_id_returns_none_for_missing_code(sqlite_session_factory: sessionmaker[Session]) -> None:
    repository = AppCodeQueryRepository(session_factory=sqlite_session_factory)

    assert repository.find_app_id("missing-code") is None
