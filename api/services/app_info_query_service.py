"""Application service for reading basic app information."""

from typing import NamedTuple, Protocol


class AppInfoRecord(NamedTuple):
    name: str
    description: str | None
    tags: tuple[str, ...]
    mode: str
    author_name: str | None


class AppInfoQuery(Protocol):
    def get_info(self, app_id: str) -> AppInfoRecord | None: ...


class AppInfoUnavailableError(Exception):
    """Raised when basic app information is unavailable."""


class AppInfoQueryService:
    def __init__(self, *, apps: AppInfoQuery) -> None:
        self._apps = apps

    def get_info(self, app_id: str) -> AppInfoRecord:
        info = self._apps.get_info(app_id)
        if info is None:
            raise AppInfoUnavailableError
        return info
