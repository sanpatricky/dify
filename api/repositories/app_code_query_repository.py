"""Database repository for resolving app codes."""

from typing import override

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from models.model import Site
from services.webapp_access_mode_query_service import AppCodeQuery


class AppCodeQueryRepository(AppCodeQuery):
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @override
    def find_app_id(self, app_code: str) -> str | None:
        with self._session_factory() as session:
            app_id = session.scalar(select(Site.app_id).where(Site.code == app_code).limit(1))
            return str(app_id) if app_id is not None else None
