"""
NightWatch Interactive Shell — REPL mode for token analysts.

Type commands like:
    research binance BTC/USDT
    board --exchange gate
    cherry balance
    bounties
    help
"""

import json
import shlex

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

HELP_TEXT = """
[bold]NightWatch Shell Commands:[/bold]

  [cyan]research[/cyan] <exchange> <symbol>   Token research data
  [cyan]board[/cyan] [--exchange X] [--limit N] Token board
  [cyan]search[/cyan] <query>                 Search tokens
  [cyan]grade[/cyan] <exchange> <symbol>       Quick grade check
  [cyan]balance[/cyan]                         Cherry balance
  [cyan]daily[/cyan]                           Claim daily Cherry
  [cyan]ledger[/cyan] [--limit N]              Cherry history
  [cyan]bounties[/cyan] [--status X]           Oracle bounties
  [cyan]feed[/cyan] [--limit N]                Activity feed
  [cyan]leaderboard[/cyan] [--period X]        Agent rankings
  [cyan]stats[/cyan]                           Oracle stats
  [cyan]targets[/cyan]                         My watchlist
  [cyan]watch[/cyan] <exchange> <symbol>       Add to watchlist
  [cyan]fields[/cyan] <exchange> <symbol>      Minable fields
  [cyan]catalog[/cyan]                         Feed catalog
  [cyan]api[/cyan]                             Show all API endpoints
  [cyan]json[/cyan] <any command>              Raw JSON output
  [cyan]help[/cyan]                            This help
  [cyan]exit[/cyan] / [cyan]quit[/cyan]                      Exit shell
"""


def interactive_shell(client):
    """Run interactive REPL."""
    console.print(Panel(
        "[bold yellow]NightWatch Intelligence Shell[/bold yellow]\n"
        "[dim]Type 'help' for commands, 'exit' to quit[/dim]",
        border_style="yellow",
    ))

    while True:
        try:
            raw = console.input("[bold yellow]nw>[/bold yellow] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = raw.split()

        cmd = parts[0].lower()
        args = parts[1:]
        as_json = False

        if cmd == "json" and args:
            as_json = True
            cmd = args[0].lower()
            args = args[1:]

        try:
            _dispatch(client, cmd, args, as_json)
        except SystemExit:
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def _dispatch(client, cmd, args, as_json):
    if cmd in ("exit", "quit", "q"):
        raise SystemExit

    if cmd == "help":
        console.print(HELP_TEXT)
        return

    if cmd == "research" and len(args) >= 2:
        data = client.research(args[0], args[1])
        if as_json:
            _pjson(data)
        else:
            _show_research(data, args[0], args[1])
        return

    if cmd == "grade" and len(args) >= 2:
        data = client.research(args[0], args[1])
        grade = data.get("grade", "?") if isinstance(data, dict) else "?"
        gpa = data.get("gpa", "?") if isinstance(data, dict) else "?"
        console.print(f"[bold]{args[1]}[/bold] on {args[0]}: Grade [yellow bold]{grade}[/yellow bold] (GPA: {gpa})")
        return

    if cmd == "board":
        exchange = _opt(args, "--exchange") or _opt(args, "-e")
        limit = int(_opt(args, "--limit") or _opt(args, "-n") or "20")
        data = client.board(exchange=exchange, limit=limit)
        if as_json:
            _pjson(data)
        else:
            _show_board(data, limit)
        return

    if cmd == "search" and args:
        data = client.search_tokens(" ".join(args))
        _pjson(data)
        return

    if cmd == "balance":
        data = client.cherry_balance()
        if as_json:
            _pjson(data)
        else:
            bal = data.get("balance", data.get("cherry_balance", 0))
            console.print(f"Cherry Balance: [bold yellow]{bal:,}[/bold yellow]")
        return

    if cmd == "daily":
        data = client.cherry_claim_daily()
        console.print(f"[green]Claimed![/green] {data}")
        return

    if cmd == "ledger":
        limit = int(_opt(args, "--limit") or "20")
        _pjson(client.cherry_ledger(limit=limit))
        return

    if cmd == "bounties":
        status = _opt(args, "--status") or "open"
        data = client.bounties(status=status)
        if as_json:
            _pjson(data)
        else:
            _show_bounties(data)
        return

    if cmd == "feed":
        limit = int(_opt(args, "--limit") or "15")
        data = client.oracle_feed(limit=limit)
        if as_json:
            _pjson(data)
        else:
            _show_feed(data)
        return

    if cmd == "leaderboard":
        period = _opt(args, "--period") or "all"
        _pjson(client.leaderboard(period=period))
        return

    if cmd == "stats":
        _pjson(client.oracle_stats())
        return

    if cmd == "targets":
        _pjson(client.my_targets())
        return

    if cmd == "watch" and len(args) >= 2:
        data = client.add_target(args[0], args[1])
        console.print(f"[green]Added {args[1]} on {args[0]} to watchlist[/green]")
        return

    if cmd == "fields" and len(args) >= 2:
        _pjson(client.mining_fields(args[0], args[1]))
        return

    if cmd == "catalog":
        _pjson(client.feed_catalog())
        return

    if cmd == "api":
        spec = client.openapi_spec()
        paths = spec.get("paths", {})
        console.print(f"[bold]{len(paths)} endpoints[/bold]")
        for p, methods in sorted(paths.items()):
            for m in methods:
                console.print(f"  [cyan]{m.upper():6s}[/cyan] {p}")
        return

    console.print(f"[dim]Unknown command: {cmd}. Type 'help' for options.[/dim]")


def _opt(args, flag):
    """Extract --flag value from args list."""
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return None


def _pjson(data):
    console.print_json(json.dumps(data, default=str, ensure_ascii=False))


def _show_research(data, exchange, symbol):
    if not isinstance(data, dict):
        _pjson(data)
        return
    console.print(Panel(
        f"Grade: [bold yellow]{data.get('grade', '?')}[/bold yellow]  "
        f"GPA: [bold]{data.get('gpa', '?')}[/bold]  "
        f"Lifecycle: {data.get('lifecycle', '?')}\n"
        f"Volume 24h: ${data.get('volume_24h_usd', 0):,.0f}  "
        f"Spread: {data.get('spread_pct', 0):.4f}%  "
        f"Depth: ${data.get('total_depth_usd', 0):,.0f}",
        title=f"{symbol} on {exchange}",
        border_style="blue",
    ))


def _show_board(data, limit):
    tokens = data.get("tokens", data) if isinstance(data, dict) else data
    if not isinstance(tokens, list):
        _pjson(data)
        return
    table = Table(title="Token Board")
    table.add_column("#", width=4)
    table.add_column("Exchange")
    table.add_column("Symbol", style="bold")
    table.add_column("Grade", style="yellow")
    table.add_column("GPA", justify="right")
    for i, t in enumerate(tokens[:limit], 1):
        if isinstance(t, dict):
            table.add_row(str(i), t.get("exchange", ""), t.get("symbol", ""),
                          t.get("grade", ""), f"{t.get('gpa', 0):.2f}")
    console.print(table)


def _show_bounties(data):
    items = data.get("items", [])
    table = Table(title="Oracle Bounties")
    table.add_column("ID", width=5)
    table.add_column("Token", style="bold")
    table.add_column("Task")
    table.add_column("Cherry", style="yellow", justify="right")
    for b in items:
        table.add_row(
            str(b.get("id")), f"{b.get('exchange','')}/{b.get('symbol','')}",
            b.get("task_description", "")[:50], str(b.get("cherry_reward", 0)),
        )
    console.print(table)


def _show_feed(data):
    for item in data.get("items", []):
        agent = item.get("agent_label") or f"Agent #{item.get('user_id', '?')}"
        summary = item.get("summary", "")
        ts = str(item.get("created_at", ""))[:19]
        console.print(f"[dim]{ts}[/dim] [bold]{agent}[/bold] {summary}")
