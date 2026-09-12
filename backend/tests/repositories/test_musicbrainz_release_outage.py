"""Transient catalog failures must not masquerade as missing exact editions."""
from unittest.mock import AsyncMock

import httpx
import pytest

from core.exceptions import ExternalServiceError
from repositories.musicbrainz_album import MusicBrainzAlbumMixin


class Repo(MusicBrainzAlbumMixin):
    def __init__(self):
        self._cache = AsyncMock()
        self._cache.get.return_value = None


@pytest.mark.asyncio
async def test_release_network_outage_is_retryable_and_not_cached(monkeypatch):
    fetch = AsyncMock(side_effect=httpx.ConnectError("TLS connection closed"))
    monkeypatch.setattr("repositories.musicbrainz_album.mb_api_get", fetch)
    repo = Repo()
    with pytest.raises(ExternalServiceError, match="temporarily unavailable"):
        await repo.get_release_by_id("selected-release")
    repo._cache.set.assert_not_awaited()
    fetch.side_effect = None
    fetch.return_value = {"id": "selected-release", "media": [{"tracks": []}]}
    assert (await repo.get_release_by_id("selected-release"))["id"] == "selected-release"
    assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_release_missing_remains_distinct_from_outage(monkeypatch):
    monkeypatch.setattr("repositories.musicbrainz_album.mb_api_get", AsyncMock(return_value={}))
    assert await Repo().get_release_by_id("missing-release") is None


@pytest.mark.asyncio
async def test_release_group_stream_reset_recovers_without_negative_cache(monkeypatch):
    fetch = AsyncMock(side_effect=httpx.RemoteProtocolError("HTTP/2 stream reset"))
    monkeypatch.setattr("repositories.musicbrainz_album.mb_api_get", fetch)
    repo = Repo()
    with pytest.raises(ExternalServiceError, match="temporarily unavailable"):
        await repo.get_release_group_by_id("selected-album")
    repo._cache.set.assert_not_awaited()
    fetch.side_effect = None
    fetch.return_value = {"id": "selected-album", "releases": [{"id": "edition"}]}
    assert (await repo.get_release_group_by_id("selected-album"))["id"] == "selected-album"
    assert fetch.await_count == 2
