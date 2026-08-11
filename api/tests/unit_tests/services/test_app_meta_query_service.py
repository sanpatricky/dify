from unittest.mock import MagicMock, create_autospec

import pytest

from services.app_meta_query_service import AppMetaQuery, AppMetaQueryService, AppMetaToolRecord


def _service(*tools: AppMetaToolRecord) -> tuple[AppMetaQueryService, MagicMock]:
    metadata: MagicMock = create_autospec(AppMetaQuery, instance=True, spec_set=True)
    metadata.get_tool_icon_sources.return_value = tools
    return (
        AppMetaQueryService(
            metadata=metadata,
            builtin_icon_url_prefix="https://console.example/console/api/workspaces/current/tool-provider/builtin/",
        ),
        metadata,
    )


def test_get_meta_maps_builtin_and_api_icons() -> None:
    service, metadata = _service(
        AppMetaToolRecord("builtin", "search", "search", None),
        AppMetaToolRecord("api", "provider-1", "weather", '{"background":"#fff","content":"W"}'),
        AppMetaToolRecord("workflow", "ignored", "ignored", None),
    )

    result = service.get_meta("app-1")

    assert result == {
        "tool_icons": {
            "search": "https://console.example/console/api/workspaces/current/tool-provider/builtin/search/icon",
            "weather": {"background": "#fff", "content": "W"},
        }
    }
    metadata.get_tool_icon_sources.assert_called_once_with("app-1")


@pytest.mark.parametrize("provider_icon", [None, "not-json"])
def test_get_meta_falls_back_for_unavailable_api_icon(provider_icon: str | None) -> None:
    service, _ = _service(AppMetaToolRecord("api", "provider-1", "weather", provider_icon))

    assert service.get_meta("app-1") == {
        "tool_icons": {"weather": {"background": "#252525", "content": "\ud83d\ude01"}}
    }


def test_get_meta_keeps_last_icon_for_duplicate_tool_name() -> None:
    service, _ = _service(
        AppMetaToolRecord("builtin", "first", "search", None),
        AppMetaToolRecord("builtin", "second", "search", None),
    )

    assert service.get_meta("app-1")["tool_icons"]["search"].endswith("/second/icon")


def test_get_meta_rejects_missing_app() -> None:
    metadata = create_autospec(AppMetaQuery, instance=True, spec_set=True)
    metadata.get_tool_icon_sources.return_value = None
    service = AppMetaQueryService(metadata=metadata, builtin_icon_url_prefix="")

    with pytest.raises(ValueError, match="App not found"):
        service.get_meta("missing")
