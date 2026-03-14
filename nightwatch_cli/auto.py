"""
NightWatch Autonomous Agent — Goal-driven mining with optional LLM reasoning.

Usage:
    agent = AutoAgent(client, goal="Mine metadata for low-cap tokens on Gate.io")
    agent.run(max_tasks=50)

Without ANTHROPIC_API_KEY: runs simple heuristic mining loop.
With ANTHROPIC_API_KEY: uses LLM to decide actions based on goal and context.
"""

import logging
import os
import random
import time

from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


class AutoAgent:
    """Goal-driven autonomous agent for NightWatch."""

    def __init__(self, client, goal: str | None = None):
        self.client = client
        self.goal = goal or "Mine data and earn Cherry tokens"
        self.history: list[dict] = []
        self.llm_available = bool(os.getenv("ANTHROPIC_API_KEY"))

    def run(self, max_tasks: int = 10, interval: int = 30):
        """Main agent loop."""
        console.print(Panel(
            f"[bold]Goal:[/bold] {self.goal}\n"
            f"[bold]Mode:[/bold] {'LLM-driven' if self.llm_available else 'Heuristic'}\n"
            f"[bold]Max tasks:[/bold] {max_tasks}",
            title="NightWatch Auto Agent",
            border_style="green",
        ))

        completed = 0
        cycle = 0

        while completed < max_tasks:
            cycle += 1
            try:
                if self.llm_available:
                    action = self._llm_decide(cycle)
                else:
                    action = self._heuristic_decide(cycle)

                console.print(f"[dim]Cycle {cycle}:[/dim] {action['type']} — {action.get('reason', '')}")

                result = self._execute(action)
                self.history.append({"cycle": cycle, "action": action, "result": result})

                if result.get("success"):
                    completed += 1
                    cherry = result.get("cherry", 0)
                    if cherry:
                        console.print(f"  [yellow]+ {cherry} Cherry[/yellow]")

                time.sleep(interval)

            except KeyboardInterrupt:
                console.print("\n[dim]Agent stopped by user.[/dim]")
                break
            except Exception as e:
                logger.error(f"Cycle {cycle} error: {e}")
                time.sleep(interval)

        console.print(Panel(
            f"[bold]Completed:[/bold] {completed}/{max_tasks} tasks\n"
            f"[bold]Cycles:[/bold] {cycle}",
            title="Agent Summary",
            border_style="green",
        ))

    def _heuristic_decide(self, cycle: int) -> dict:
        """Simple heuristic action selection."""
        actions = [
            {"type": "claim_daily", "reason": "Daily Cherry claim", "weight": 5},
            {"type": "check_bounties", "reason": "Look for open bounties", "weight": 30},
            {"type": "mine_metadata", "reason": "Mine empty token fields", "weight": 40},
            {"type": "check_feed", "reason": "Monitor oracle activity", "weight": 15},
            {"type": "explore_board", "reason": "Discover tokens to analyze", "weight": 10},
        ]

        if cycle == 1:
            return {"type": "claim_daily", "reason": "Start with daily claim"}

        total = sum(a["weight"] for a in actions)
        r = random.uniform(0, total)
        cumulative = 0
        for a in actions:
            cumulative += a["weight"]
            if r <= cumulative:
                return a
        return actions[0]

    def _llm_decide(self, cycle: int) -> dict:
        """LLM-driven action decision (requires ANTHROPIC_API_KEY)."""
        try:
            import anthropic
            client = anthropic.Anthropic()

            # Build context
            recent = self.history[-5:] if self.history else []
            context = (
                f"You are an autonomous NightWatch agent. Your goal: {self.goal}\n"
                f"Cycle: {cycle}. Recent actions: {recent}\n\n"
                f"Available actions:\n"
                f"- claim_daily: Claim daily Cherry reward\n"
                f"- check_bounties: Look for open bounties to fulfill\n"
                f"- mine_metadata: Find empty token fields and submit data\n"
                f"- submit_analysis: Submit token analysis report\n"
                f"- check_feed: Monitor oracle activity feed\n"
                f"- explore_board: Browse tokens for opportunities\n\n"
                f"Return JSON: {{\"type\": \"action_name\", \"reason\": \"why\", "
                f"\"params\": {{\"exchange\": \"...\", \"symbol\": \"...\"}}}}"
            )

            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": context}],
            )

            import json
            text = resp.content[0].text
            # Extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])

        except Exception as e:
            logger.warning(f"LLM decision failed, falling back to heuristic: {e}")

        return self._heuristic_decide(cycle)

    def _execute(self, action: dict) -> dict:
        """Execute a decided action."""
        atype = action["type"]
        params = action.get("params", {})

        try:
            if atype == "claim_daily":
                r = self.client.cherry_claim_daily()
                return {"success": True, "cherry": r.get("amount", 0), "data": r}

            if atype == "check_bounties":
                r = self.client.bounties(status="open")
                items = r.get("items", [])
                return {"success": bool(items), "count": len(items), "data": items[:3]}

            if atype == "mine_metadata":
                exchange = params.get("exchange", "binance")
                symbol = params.get("symbol", "BTC/USDT")
                r = self.client.mining_fields(exchange, symbol)
                fields = r.get("empty_fields", []) if isinstance(r, dict) else []
                return {"success": bool(fields), "fields": len(fields), "data": r}

            if atype == "submit_analysis":
                exchange = params.get("exchange", "binance")
                symbol = params.get("symbol", "BTC/USDT")
                r = self.client.submit_work(
                    "data_validate", exchange, symbol,
                    {"analysis": "Automated analysis", "confidence": 0.7},
                )
                return {"success": True, "data": r}

            if atype == "check_feed":
                r = self.client.oracle_feed(limit=10)
                items = r.get("items", [])
                return {"success": True, "count": len(items)}

            if atype == "explore_board":
                r = self.client.board(limit=10)
                return {"success": True, "data": r}

            return {"success": False, "error": f"Unknown action: {atype}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
