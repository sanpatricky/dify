"""Application service for reading app tool metadata."""

import json
from collections.abc import Sequence
from typing import Any, NamedTuple, Protocol, TypedDict


class AppMetaToolRecord(NamedTuple):
    provider_type: str
    provider_id: str
    tool_name: str
    provider_icon: str | None


class AppMetaQuery(Protocol):
    def get_tool_icon_sources(self, app_id: str) -> Sequence[AppMetaToolRecord] | None: ...


class AppMetaDict(TypedDict):
    tool_icons: dict[str, Any]


_API_TOOL_FALLBACK_ICON = {"background": "#252525", "content": "\ud83d\ude01"}


class AppMetaQueryService:
    def __init__(self, *, metadata: AppMetaQuery, builtin_icon_url_prefix: str) -> None:
        self._metadata = metadata
        self._builtin_icon_url_prefix = builtin_icon_url_prefix

    def get_meta(self, app_id: str) -> AppMetaDict:
        tools = self._metadata.get_tool_icon_sources(app_id)
        if tools is None:
            raise ValueError("App not found")

        tool_icons: dict[str, Any] = {}
        for tool in tools:
            if tool.provider_type == "builtin":
                tool_icons[tool.tool_name] = self._builtin_icon_url_prefix + tool.provider_id + "/icon"
            elif tool.provider_type == "api":
                try:
                    if tool.provider_icon is None:
                        raise ValueError("API tool provider not found")
                    tool_icons[tool.tool_name] = json.loads(tool.provider_icon)
                except (TypeError, ValueError):
                    tool_icons[tool.tool_name] = _API_TOOL_FALLBACK_ICON.copy()

        return {"tool_icons": tool_icons}
