"""Abuse limits for the analyst chat: a per-client window and a global daily quota.

Every accepted question may become a paid call to the model provider, so the public chat is
bounded twice: each client gets a few questions per window, and the whole server gets a fixed
number per UTC day. Counters live in memory, in this process only (see docs/DEPLOYMENT.md for
what that means with restarts and several instances).
"""

from __future__ import annotations

import ipaddress
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

DEFAULT_CLIENT_LIMIT = 10
DEFAULT_CLIENT_WINDOW_SECONDS = 3600
DEFAULT_DAILY_LIMIT = 200
# Beyond this many tracked clients, idle ones are dropped so memory stays bounded.
MAX_TRACKED_CLIENTS = 10_000
UNKNOWN_CLIENT = "unknown"


def _int_env(env: Mapping[str, str], name: str, default: int, minimum: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from error
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}, got {value}")
    return value


@dataclass(frozen=True)
class RateLimitConfig:
    """Limits for POST /v2/analyst/chat. A limit of 0 turns that limit off."""

    client_limit: int = DEFAULT_CLIENT_LIMIT
    client_window_seconds: int = DEFAULT_CLIENT_WINDOW_SECONDS
    daily_limit: int = DEFAULT_DAILY_LIMIT
    # A header set by the edge proxy that holds the real client address (one value, which the
    # proxy overwrites). Empty means: use the TCP peer and ignore every forwarded header.
    client_ip_header: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RateLimitConfig:
        env = os.environ if env is None else env
        return cls(
            client_limit=_int_env(env, "ANAC_ANALYST_CLIENT_LIMIT", DEFAULT_CLIENT_LIMIT, 0),
            client_window_seconds=_int_env(
                env, "ANAC_ANALYST_CLIENT_WINDOW_SECONDS", DEFAULT_CLIENT_WINDOW_SECONDS, 1
            ),
            daily_limit=_int_env(env, "ANAC_ANALYST_DAILY_LIMIT", DEFAULT_DAILY_LIMIT, 0),
            client_ip_header=env.get("ANAC_CLIENT_IP_HEADER", "").strip().lower(),
        )


@dataclass(frozen=True)
class Decision:
    allowed: bool
    scope: Literal["client", "daily"] | None = None
    retry_after: int = 0


def client_address(peer: str | None, headers: Mapping[str, str], config: RateLimitConfig) -> str:
    """The address to count against. Forwarded headers are trusted only when configured.

    X-Forwarded-For is never read: on Render the proxy appends to whatever the client sent,
    so its first entry is chosen by the client. A configured single-value header set by the
    edge (Cloudflare's CF-Connecting-IP on Render) is used only if it parses as an address.
    """
    if config.client_ip_header:
        value = headers.get(config.client_ip_header, "").strip()
        if value:
            try:
                return str(ipaddress.ip_address(value))
            except ValueError:
                pass
    return peer or UNKNOWN_CLIENT


class RateLimiter:
    """Thread-safe: FastAPI runs sync handlers in a thread pool."""

    def __init__(
        self,
        config: RateLimitConfig,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.config = config
        self._clock = clock
        self._now = now
        self._lock = threading.Lock()
        self._clients: dict[str, deque[float]] = {}
        self._day = ""
        self._day_count = 0

    def check(self, client: str) -> Decision:
        """Count one question for this client, unless a limit refuses it.

        A refused question consumes nothing, so a client hammering the endpoint does not
        burn the shared daily quota.
        """
        config = self.config
        with self._lock:
            moment = self._clock()
            today = self._now()
            day = today.date().isoformat()
            if day != self._day:
                self._day, self._day_count = day, 0

            stamps: deque[float] | None = None
            if config.client_limit > 0:
                stamps = self._clients.get(client)
                if stamps is None:
                    self._prune(moment)
                    stamps = self._clients.setdefault(client, deque())
                horizon = moment - config.client_window_seconds
                while stamps and stamps[0] <= horizon:
                    stamps.popleft()
                if len(stamps) >= config.client_limit:
                    wait = stamps[0] + config.client_window_seconds - moment
                    return Decision(False, "client", max(1, math.ceil(wait)))

            if config.daily_limit > 0 and self._day_count >= config.daily_limit:
                midnight = datetime.combine(
                    today.date() + timedelta(days=1), datetime.min.time(), UTC
                )
                wait = (midnight - today).total_seconds()
                return Decision(False, "daily", max(1, math.ceil(wait)))

            if stamps is not None:
                stamps.append(moment)
            self._day_count += 1
            return Decision(True)

    def _prune(self, moment: float) -> None:
        if len(self._clients) < MAX_TRACKED_CLIENTS:
            return
        horizon = moment - self.config.client_window_seconds
        idle = [key for key, stamps in self._clients.items() if not stamps or stamps[-1] <= horizon]
        for key in idle:
            del self._clients[key]
        # Still full of active clients: drop the oldest-seen ones rather than grow forever.
        while len(self._clients) >= MAX_TRACKED_CLIENTS:
            del self._clients[next(iter(self._clients))]
