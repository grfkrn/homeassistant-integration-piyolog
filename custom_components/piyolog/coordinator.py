"""Data update coordinator for the PiyoLog integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEED_URL,
    CONF_FEED_URL_LONG,
    DOMAIN,
    LONG_FEED_MIN_INTERVAL_MINUTES,
)
from .feed import (
    AggregatedData,
    FeedHttpError,
    FeedSnapshot,
    aggregate,
    fetch_feed,
    merge_snapshots,
)
from .statistics import async_import_feed_statistics

_LOGGER = logging.getLogger(__name__)

ISSUE_FEED_UNAVAILABLE = "feed_unavailable"
_ISSUE_AFTER_CONSECUTIVE_404 = 3


class PiyologCoordinator(DataUpdateCoordinator[AggregatedData]):
    """Fetch the main feed every update; the long feed at most every 15 min."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._feed_url: str = entry.data[CONF_FEED_URL]
        self._feed_url_long: str | None = entry.data.get(CONF_FEED_URL_LONG)
        self._long_snapshot: FeedSnapshot | None = None
        self._long_last_fetch: datetime | None = None
        self._long_last_error: str | None = None
        self._consecutive_404 = 0
        self._statistics_state: dict = {}

    async def _async_update_data(self) -> AggregatedData:
        session = async_get_clientsession(self.hass)
        try:
            main_snapshot = await fetch_feed(session, self._feed_url)
        except FeedHttpError as err:
            self._track_http_error(err.status)
            raise UpdateFailed(f"Feed request failed: HTTP {err.status}") from err
        except Exception as err:  # FeedError and anything unexpected
            raise UpdateFailed(f"Feed request failed: {err}") from err
        self._track_success()

        snapshots = [main_snapshot]
        if self._feed_url_long:
            long_snapshot = await self._fetch_long(session)
            if long_snapshot is not None:
                snapshots.append(long_snapshot)

        records = merge_snapshots(snapshots)
        generated_at = max(s.generated_at for s in snapshots)
        data = aggregate(
            records,
            tz=dt_util.get_default_time_zone(),
            now=dt_util.utcnow(),
            generated_at=generated_at,
        )
        # Backfill long-term statistics with the feed's past records.
        async_import_feed_statistics(self.hass, data, self._statistics_state)
        return data

    async def _fetch_long(
        self, session
    ) -> FeedSnapshot | None:
        """Fetch the long-period feed, respecting its cache lifetime."""
        now = datetime.now(timezone.utc)
        min_interval = timedelta(minutes=LONG_FEED_MIN_INTERVAL_MINUTES)
        if (
            self._long_snapshot is not None
            and self._long_last_fetch is not None
            and now - self._long_last_fetch < min_interval
        ):
            return self._long_snapshot
        try:
            snapshot = await fetch_feed(session, self._feed_url_long)  # type: ignore[arg-type]
        except Exception as err:  # noqa: BLE001 - long feed is best-effort
            self._long_last_error = str(err)
            _LOGGER.debug("Long feed fetch failed (keeping cache): %s", err)
            return self._long_snapshot
        self._long_snapshot = snapshot
        self._long_last_fetch = now
        self._long_last_error = None
        return snapshot

    def _track_http_error(self, status: int) -> None:
        if status != 404:
            self._consecutive_404 = 0
            return
        self._consecutive_404 += 1
        if self._consecutive_404 == _ISSUE_AFTER_CONSECUTIVE_404:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_FEED_UNAVAILABLE}_{self.config_entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_FEED_UNAVAILABLE,
            )

    def _track_success(self) -> None:
        if self._consecutive_404:
            self._consecutive_404 = 0
            ir.async_delete_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_FEED_UNAVAILABLE}_{self.config_entry.entry_id}",
            )
