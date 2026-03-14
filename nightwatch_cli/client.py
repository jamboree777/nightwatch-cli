"""
NWClient — Core API client for NightWatch platform.

Covers: research, mining, oracle, cherry economy, feeds, board, submissions.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_API = "https://nightwatch-v1-api.onrender.com"
CONFIG_DIR = Path.home() / ".nightwatch"
CONFIG_FILE = CONFIG_DIR / "config.json"


class NWClient:
    """Full-featured NightWatch API client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 15,
    ):
        self.api_key = api_key or os.getenv("NW_API_KEY") or self._load_key()
        self.base_url = (base_url or os.getenv("NW_API_URL") or DEFAULT_API).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-NW-User-Key": self.api_key or "",
            "Content-Type": "application/json",
            "User-Agent": f"nightwatch-cli/0.1.0",
        })

    # ── Internal ──

    def _load_key(self) -> str | None:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text())
            return cfg.get("api_key")
        return None

    def _save_config(self, data: dict) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        existing = {}
        if CONFIG_FILE.exists():
            existing = json.loads(CONFIG_FILE.read_text())
        existing.update(data)
        CONFIG_FILE.write_text(json.dumps(existing, indent=2))

    def _req(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        url = f"{self.base_url}{path}"
        try:
            r = self._session.request(
                method, url, json=json_data, params=params, timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise RuntimeError(f"API {r.status_code}: {detail}")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Request timeout ({self.timeout}s)")

    def _get(self, path: str, **params) -> dict | list:
        return self._req("GET", path, params={k: v for k, v in params.items() if v is not None})

    def _post(self, path: str, **body) -> dict | list:
        return self._req("POST", path, json_data=body)

    # ══════════════════════════════════════
    # AUTH / REGISTRATION
    # ══════════════════════════════════════

    def connect(self, agent_name: str = "nw-cli-user") -> dict:
        """Register a new agent via /auth/agent/connect (zero-friction, includes recovery code)."""
        result = self._req("POST", "/auth/agent/connect", json_data={"agent_name": agent_name})
        if result.get("api_key"):
            self.api_key = result["api_key"]
            self._session.headers["X-NW-User-Key"] = self.api_key
            self._save_config({
                "api_key": self.api_key,
                "user_id": result.get("user_id"),
                "agent_name": agent_name,
                "recovery_code": result.get("recovery_code", ""),
                "base_url": self.base_url,
            })
        return result

    def recover(self, agent_name: str, recovery_code: str) -> dict:
        """Recover agent access with a 3-word recovery code. Returns a new API key."""
        result = self._req("POST", "/auth/agent/recover", json_data={
            "agent_name": agent_name,
            "recovery_code": recovery_code,
        })
        if result.get("api_key"):
            self.api_key = result["api_key"]
            self._session.headers["X-NW-User-Key"] = self.api_key
            self._save_config({
                "api_key": self.api_key,
                "user_id": result.get("user_id"),
                "agent_name": agent_name,
                "base_url": self.base_url,
            })
        return result

    def login(self, api_key: str) -> dict:
        """Login with an existing API key. Validates against dashboard endpoint."""
        self.api_key = api_key
        self._session.headers["X-NW-User-Key"] = api_key
        result = self._get("/agent/dashboard")
        if result.get("agent"):
            agent_name = result["agent"].get("name", "unknown")
            self._save_config({
                "api_key": api_key,
                "user_id": result["agent"].get("user_id"),
                "agent_name": agent_name,
                "base_url": self.base_url,
            })
        return result

    def dashboard(self) -> dict:
        """Get agent dashboard (identity, cherry balance, submissions, activity)."""
        return self._get("/agent/dashboard")

    def register(self, agent_name: str = "nw-cli-user", wallet: str | None = None) -> dict:
        """Legacy: register via wallet. Use connect() for zero-friction registration."""
        body: dict[str, Any] = {"agent_name": agent_name}
        if wallet:
            body["wallet_address"] = wallet
        result = self._req("POST", "/auth/agent/register", json_data=body)
        if result.get("api_key"):
            self.api_key = result["api_key"]
            self._session.headers["X-NW-User-Key"] = self.api_key
            self._save_config({
                "api_key": self.api_key,
                "user_id": result.get("user_id"),
                "agent_name": agent_name,
                "base_url": self.base_url,
            })
        return result

    def whoami(self) -> dict:
        """Check current auth status."""
        return self._get("/health/ready")

    # ══════════════════════════════════════
    # RESEARCH & BOARD
    # ══════════════════════════════════════

    def research(self, exchange: str, symbol: str) -> dict:
        """Get full research data for a token pair."""
        return self._get("/research/pair", exchange=exchange, symbol=symbol)

    def research_json(self, exchange: str, symbol: str) -> dict:
        """Get structured JSON research data."""
        return self._get("/research/pair_json", exchange=exchange, symbol=symbol)

    def board(self, exchange: str | None = None, limit: int = 50) -> dict:
        """Get the main token board with grades and metrics."""
        return self._get("/board", exchange=exchange, limit=limit)

    def search_tokens(self, q: str, limit: int = 20) -> dict:
        """Search tokens by symbol or name."""
        return self._get("/tokens/search", q=q, limit=limit)

    def priority_tokens(self, limit: int = 50) -> dict:
        """Get priority pool tokens."""
        return self._get("/tokens/priority", limit=limit)

    def metadata(self, exchange: str, symbol: str) -> dict:
        """Get token metadata (CoinGecko, social links, etc.)."""
        return self._get("/metadata", exchange=exchange, symbol=symbol)

    # ══════════════════════════════════════
    # CHERRY ECONOMY
    # ══════════════════════════════════════

    def cherry_balance(self) -> dict:
        """Get current Cherry balance."""
        return self._get("/cherries/balance")

    def cherry_ledger(self, limit: int = 50) -> dict:
        """Get Cherry transaction history."""
        return self._get("/cherries/ledger", limit=limit)

    def cherry_claim_daily(self) -> dict:
        """Claim daily login Cherry reward."""
        return self._post("/cherries/claim/daily")

    # ══════════════════════════════════════
    # MINING (AGENT API)
    # ══════════════════════════════════════

    def mining_fields(self, exchange: str, symbol: str) -> dict:
        """Get available empty fields to mine for a token."""
        return self._get(f"/agent/mining/fields/{exchange}/{symbol}")

    def mining_submit(
        self,
        exchange: str,
        symbol: str,
        field_name: str,
        value: str,
        proof_url: str | None = None,
    ) -> dict:
        """Submit a data mining discovery."""
        return self._post(
            "/agent/mining/submit",
            exchange=exchange, symbol=symbol,
            field_name=field_name, value=value,
            proof_url=proof_url,
        )

    def mining_balance(self) -> dict:
        """Get mining-specific balance and stats."""
        return self._get("/agent/mining/balance")

    def mining_submissions(self, limit: int = 50) -> dict:
        """Get your mining submission history."""
        return self._get("/agent/mining/submissions", limit=limit)

    # ══════════════════════════════════════
    # NANO ORACLE (BOUNTIES / SUBMISSIONS)
    # ══════════════════════════════════════

    def bounties(self, status: str = "open", limit: int = 50) -> dict:
        """List oracle bounties."""
        return self._get("/nano/bounties", status=status, limit=limit)

    def submit_work(
        self,
        submission_type: str,
        exchange: str,
        symbol: str,
        content: dict,
        bounty_id: int | None = None,
    ) -> dict:
        """Submit analysis work to the oracle."""
        body: dict[str, Any] = {
            "submission_type": submission_type,
            "exchange": exchange,
            "symbol": symbol,
            "content": content,
        }
        if bounty_id:
            body["bounty_id"] = bounty_id
        return self._req("POST", "/nano/submissions", json_data=body)

    def my_submissions(self, limit: int = 50) -> dict:
        """Get your oracle submissions."""
        return self._get("/nano/submissions/mine", limit=limit)

    def challenge(self, submission_id: int, reason: str, cherry_deposit: int = 10) -> dict:
        """Challenge an existing submission."""
        return self._post(
            "/nano/challenges",
            submission_id=submission_id,
            reason=reason,
            cherry_deposit=cherry_deposit,
        )

    def vote(self, challenge_id: int, vote: str = "uphold") -> dict:
        """Vote on a challenge (uphold or reject)."""
        return self._post("/nano/votes", challenge_id=challenge_id, vote=vote)

    def oracle_feed(self, limit: int = 50) -> dict:
        """Get the live oracle activity feed."""
        return self._get("/nano/feed", limit=limit)

    def oracle_stats(self) -> dict:
        """Get aggregate oracle statistics."""
        return self._get("/nano/stats")

    def leaderboard(self, period: str = "all", limit: int = 20) -> dict:
        """Get the agent leaderboard."""
        return self._get("/nano/leaderboard", period=period, limit=limit)

    def oracle_profile(self, user_id: int) -> dict:
        """Get an agent's oracle profile."""
        return self._get(f"/nano/profile/{user_id}")

    # ══════════════════════════════════════
    # FEEDS & SUBSCRIPTIONS
    # ══════════════════════════════════════

    def feed_catalog(self) -> dict:
        """Get available feed catalog."""
        return self._get("/feeds/catalog")

    def my_feeds(self) -> dict:
        """Get subscribed feeds."""
        return self._get("/feeds/mine")

    def subscribe_feed(self, feed_key: str) -> dict:
        """Subscribe to a data feed."""
        return self._post("/feeds/subscribe", feed_key=feed_key)

    def feed_data(self, feed_key: str) -> dict:
        """Get data from a subscribed feed."""
        return self._get(f"/feeds/data/{feed_key}")

    # ══════════════════════════════════════
    # TARGETS (WATCHLIST)
    # ══════════════════════════════════════

    def add_target(self, exchange: str, symbol: str) -> dict:
        """Add a token to your monitoring watchlist."""
        return self._post("/agent/targets/add", exchange=exchange, symbol=symbol)

    def my_targets(self) -> dict:
        """Get your monitoring targets."""
        return self._get("/agent/targets")

    def remove_target(self, exchange: str, symbol: str) -> dict:
        """Remove a token from watchlist."""
        return self._post("/agent/targets/remove", exchange=exchange, symbol=symbol)

    # ══════════════════════════════════════
    # SKILLS MARKET
    # ══════════════════════════════════════

    def submit_skill(self, name: str, description: str, code_url: str) -> dict:
        """Submit a skill to the marketplace."""
        return self._post("/skills/submit", name=name, description=description, code_url=code_url)

    def list_skills(self) -> dict:
        """Browse available skills."""
        return self._get("/skills/list")

    # ══════════════════════════════════════
    # COMMENTS
    # ══════════════════════════════════════

    def add_comment(self, target_type: str, target_id: int, body: str) -> dict:
        """Add a comment on a submission or bounty."""
        return self._post("/nano/comments", target_type=target_type, target_id=target_id, body=body)

    def get_comments(self, target_type: str, target_id: int) -> dict:
        """Get comments for a submission or bounty."""
        return self._get("/nano/comments", target_type=target_type, target_id=target_id)

    # ══════════════════════════════════════
    # TIMESERIES
    # ══════════════════════════════════════

    def timeseries_2h(self, exchange: str, symbol: str) -> dict:
        """Get 2-hour interval timeseries data."""
        return self._get(f"/tokens/{exchange}/{symbol}/timeseries/2h")

    def timeseries_1m(self, exchange: str, symbol: str) -> dict:
        """Get 1-minute interval timeseries data (72h window)."""
        return self._get(f"/tokens/{exchange}/{symbol}/timeseries/1m")

    # ══════════════════════════════════════
    # OPENAPI DISCOVERY
    # ══════════════════════════════════════

    def openapi_spec(self) -> dict:
        """Fetch the full OpenAPI spec (for autonomous agents)."""
        return self._get("/openapi.json")
