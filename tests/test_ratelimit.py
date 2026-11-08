"""Abuse limits on the analyst chat. No test reaches a real provider."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from anac.agent.llm import LlmClient, LlmConfig
from anac.api.app import create_app
from anac.api.ratelimit import (
    MAX_TRACKED_CLIENTS,
    RateLimitConfig,
    RateLimiter,
    client_address,
)

SECRET = "gsk_test_never_shown_0123456789"


class Clock:
    def __init__(self) -> None:
        self.seconds = 1000.0
        self.day = datetime(2026, 11, 8, 23, 0, tzinfo=UTC)

    def tick(self) -> float:
        return self.seconds

    def today(self) -> datetime:
        return self.day

    def advance(self, seconds: float) -> None:
        self.seconds += seconds
        self.day += timedelta(seconds=seconds)


def limiter(clock: Clock, **overrides: object) -> RateLimiter:
    config = RateLimitConfig(
        **{"client_limit": 2, "client_window_seconds": 60, "daily_limit": 5, **overrides}
    )  # type: ignore[arg-type]
    return RateLimiter(config, clock=clock.tick, now=clock.today)


class Provider:
    """Counts calls; always answers that there is no data, without any number."""

    def __init__(self) -> None:
        self.calls = 0

    def client(self) -> LlmClient:
        def handler(request: httpx.Request) -> httpx.Response:
            self.calls += 1
            body = {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "There is no data for that."},
                        "finish_reason": "stop",
                    }
                ]
            }
            return httpx.Response(200, json=body)

        return LlmClient(
            LlmConfig("groq", "https://llm.test/v1", "m", SECRET), httpx.MockTransport(handler)
        )


@pytest.fixture
def clock() -> Clock:
    return Clock()


def app_with(tmp_path: Path, limits: RateLimiter, provider: Provider) -> TestClient:
    (tmp_path / "analyst_catalog.json").write_text(
        json.dumps({"data": {}, "meta": {}}), encoding="utf-8"
    )
    return TestClient(create_app(tmp_path, llm=provider.client(), limiter=limits))


def ask(app: TestClient, **headers: str) -> httpx.Response:
    return app.post("/v2/analyst/chat", json={"question": "Any data?"}, headers=headers)


# --- the limiter itself -------------------------------------------------------------------


def test_a_client_is_refused_past_its_limit_then_allowed_after_the_window(clock: Clock) -> None:
    limits = limiter(clock)
    assert limits.check("a").allowed
    clock.advance(10)
    assert limits.check("a").allowed
    refused = limits.check("a")
    assert (refused.allowed, refused.scope, refused.retry_after) == (False, "client", 50)
    clock.advance(50)
    assert limits.check("a").allowed


def test_clients_are_counted_separately(clock: Clock) -> None:
    limits = limiter(clock)
    assert limits.check("a").allowed and limits.check("a").allowed
    assert not limits.check("a").allowed
    assert limits.check("b").allowed


def test_the_daily_quota_is_shared_and_resets_at_utc_midnight(clock: Clock) -> None:
    limits = limiter(clock, client_limit=0)
    for index in range(5):
        assert limits.check(f"client-{index}").allowed
    refused = limits.check("someone-new")
    assert (refused.allowed, refused.scope) == (False, "daily")
    assert refused.retry_after == 3600  # 23:00 UTC -> midnight
    clock.advance(3600)
    assert limits.check("someone-new").allowed


def test_refused_questions_do_not_consume_the_daily_quota(clock: Clock) -> None:
    limits = limiter(clock, client_limit=1, daily_limit=2)
    assert limits.check("abuser").allowed
    for _ in range(50):
        assert not limits.check("abuser").allowed
    assert limits.check("visitor").allowed


def test_zero_turns_a_limit_off(clock: Clock) -> None:
    limits = limiter(clock, client_limit=0, daily_limit=0)
    assert all(limits.check("a").allowed for _ in range(500))


def test_memory_stays_bounded_with_many_clients(clock: Clock) -> None:
    limits = limiter(clock, daily_limit=0)
    for index in range(MAX_TRACKED_CLIENTS + 50):
        limits.check(f"10.0.{index // 256}.{index % 256}")
    assert len(limits._clients) <= MAX_TRACKED_CLIENTS


# --- configuration ------------------------------------------------------------------------


def test_config_defaults_and_overrides() -> None:
    assert RateLimitConfig.from_env({}) == RateLimitConfig()
    config = RateLimitConfig.from_env({
        "ANAC_ANALYST_CLIENT_LIMIT": "3",
        "ANAC_ANALYST_CLIENT_WINDOW_SECONDS": "120",
        "ANAC_ANALYST_DAILY_LIMIT": "50",
        "ANAC_CLIENT_IP_HEADER": "CF-Connecting-IP",
    })  # fmt: skip
    assert config == RateLimitConfig(3, 120, 50, "cf-connecting-ip")


@pytest.mark.parametrize(
    "env",
    [
        {"ANAC_ANALYST_CLIENT_LIMIT": "ten"},
        {"ANAC_ANALYST_DAILY_LIMIT": "-1"},
        {"ANAC_ANALYST_CLIENT_WINDOW_SECONDS": "0"},
    ],
)
def test_invalid_config_fails_at_startup(env: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="ANAC_"):
        RateLimitConfig.from_env(env)


# --- client address -----------------------------------------------------------------------


def test_forwarded_headers_are_ignored_by_default() -> None:
    headers = {
        "x-forwarded-for": "1.2.3.4",
        "cf-connecting-ip": "5.6.7.8",
        "true-client-ip": "9.9.9.9",
    }
    assert client_address("10.0.0.7", headers, RateLimitConfig()) == "10.0.0.7"


def test_only_the_configured_header_is_trusted_and_x_forwarded_for_never() -> None:
    config = RateLimitConfig(client_ip_header="cf-connecting-ip")
    headers = {"x-forwarded-for": "1.2.3.4, 8.8.8.8", "cf-connecting-ip": "203.0.113.9"}
    assert client_address("10.0.0.7", headers, config) == "203.0.113.9"
    assert client_address("10.0.0.7", {"x-forwarded-for": "1.2.3.4"}, config) == "10.0.0.7"


@pytest.mark.parametrize("value", ["not-an-ip", "1.2.3.4, 5.6.7.8", "", "../../etc"])
def test_a_malformed_header_falls_back_to_the_peer(value: str) -> None:
    config = RateLimitConfig(client_ip_header="cf-connecting-ip")
    assert client_address("10.0.0.7", {"cf-connecting-ip": value}, config) == "10.0.0.7"


def test_ipv6_is_normalised() -> None:
    config = RateLimitConfig(client_ip_header="cf-connecting-ip")
    headers = {"cf-connecting-ip": "2001:DB8:0:0::1"}
    assert client_address(None, headers, config) == "2001:db8::1"


# --- through the API ----------------------------------------------------------------------


def test_the_api_returns_429_with_retry_after_and_never_calls_the_provider(
    tmp_path: Path, clock: Clock
) -> None:
    provider = Provider()
    app = app_with(tmp_path, limiter(clock), provider)
    assert ask(app).status_code == 200
    assert ask(app).status_code == 200
    response = ask(app)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert response.json()["detail"] == {
        "code": "rate_limited",
        "scope": "client",
        "message": "Too many questions from this connection. Please wait before asking again.",
    }
    assert provider.calls == 2
    assert SECRET not in response.text


def test_spoofing_x_forwarded_for_does_not_reset_the_limit(tmp_path: Path, clock: Clock) -> None:
    provider = Provider()
    app = app_with(tmp_path, limiter(clock), provider)
    statuses = [ask(app, **{"X-Forwarded-For": f"198.51.100.{n}"}).status_code for n in range(4)]
    assert statuses == [200, 200, 429, 429]
    assert provider.calls == 2


def test_behind_the_edge_each_visitor_has_its_own_limit(tmp_path: Path, clock: Clock) -> None:
    provider = Provider()
    app = app_with(tmp_path, limiter(clock, client_ip_header="cf-connecting-ip"), provider)
    first = [ask(app, **{"CF-Connecting-IP": "203.0.113.1"}).status_code for _ in range(3)]
    second = ask(app, **{"CF-Connecting-IP": "203.0.113.2"}).status_code
    assert first == [200, 200, 429]
    assert second == 200


def test_the_daily_quota_answers_429_until_midnight(tmp_path: Path, clock: Clock) -> None:
    provider = Provider()
    app = app_with(tmp_path, limiter(clock, client_limit=0, daily_limit=1), provider)
    assert ask(app).status_code == 200
    response = ask(app)
    assert response.status_code == 429
    assert response.json()["detail"]["scope"] == "daily"
    assert response.headers["retry-after"] == "3600"
    assert provider.calls == 1


def test_invalid_requests_do_not_count(tmp_path: Path, clock: Clock) -> None:
    provider = Provider()
    app = app_with(tmp_path, limiter(clock, client_limit=1), provider)
    for _ in range(5):
        assert app.post("/v2/analyst/chat", json={"question": ""}).status_code == 422
    assert ask(app).status_code == 200


def test_other_endpoints_are_not_limited(tmp_path: Path, clock: Clock) -> None:
    app = app_with(tmp_path, limiter(clock, client_limit=1, daily_limit=1), Provider())
    ask(app)
    assert ask(app).status_code == 429
    assert all(app.get("/v2/analyst/config").status_code == 200 for _ in range(10))


def test_limits_come_from_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANAC_ANALYST_CLIENT_LIMIT", "1")
    provider = Provider()
    app = TestClient(create_app(tmp_path, llm=provider.client()))
    assert ask(app).status_code == 200
    assert ask(app).status_code == 429
