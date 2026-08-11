"""Database repository for basic app information."""

from typing import override

from sqlalchemy.orm import Session, sessionmaker

from models.model import App
from services.app_info_query_service import AppInfoQuery, AppInfoRecord


class AppInfoQueryRepository(AppInfoQuery):
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @override
    def get_info(self, app_id: str) -> AppInfoRecord | None:
        with self._session_factory() as session:
            app = session.get(App, app_id)
            if app is None:
                return None

            return AppInfoRecord(
                name=app.name,
                description=app.description,
                tags=tuple(tag.name for tag in app.tags_with_session(session=session)),
                mode=app.mode.value,
                author_name=app.author_name_with_session(session=session),
            )
