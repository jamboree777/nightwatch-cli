"""
NightWatch CLI — Command-line interface for token analysts and agents.

Commands:
    nw init              Register and get API key
    nw research          Token research data
    nw board             View token board
    nw mine              Mining operations
    nw cherry            Cherry economy
    nw oracle            Oracle bounties & submissions
    nw feed              Data feeds
    nw shell             Interactive REPL
    nw auto              Autonomous agent mode
"""

import json
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .client import NWClient, CONFIG_FILE

console = Console()


def get_client(api_key: str | None = None, api_url: str | None = None) -> NWClient:
    try:
        return NWClient(api_key=api_key, base_url=api_url)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("Run [bold]nw init[/bold] to register first.")
        sys.exit(1)


def print_json(data):
    console.print_json(json.dumps(data, default=str, ensure_ascii=False))


# ══════════════════════════════════════
# ROOT GROUP
# ══════════════════════════════════════

@click.group()
@click.version_option(__version__, prog_name="nightwatch-cli")
def main():
    """NightWatch — Intelligence Layer for Token Analysts."""
    pass


# ══════════════════════════════════════
# INIT
# ══════════════════════════════════════

@main.command()
@click.option("--name", prompt="Agent name", help="Agent display name")
@click.option("--api-url", default=None, help="Custom API URL")
def init(name, api_url):
    """Register with NightWatch and get your API key."""
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        if cfg.get("api_key"):
            console.print(Panel(
                f"[green]Already registered![/green]\n"
                f"Agent: [bold]{cfg.get('agent_name', 'unknown')}[/bold]\n"
                f"User ID: {cfg.get('user_id', '?')}\n"
                f"Key: {cfg['api_key'][:8]}...{cfg['api_key'][-4:]}",
                title="NightWatch Config",
            ))
            if not click.confirm("Re-register with a new identity?"):
                return

    client = NWClient(api_key="pending", base_url=api_url)
    console.print("[dim]Connecting to NightWatch...[/dim]")

    try:
        result = client.connect(agent_name=name)
        recovery = result.get("recovery_code", "")
        console.print(Panel(
            f"[green bold]Connected![/green bold]\n\n"
            f"Agent Name: [bold]{result.get('agent_name', name)}[/bold]\n"
            f"User ID: {result.get('user_id', '?')}\n"
            f"API Key: [bold]{result.get('api_key', '?')}[/bold]\n\n"
            f"[yellow bold]Recovery Code: {recovery}[/yellow bold]\n"
            f"[yellow]Save this! You need it to recover your key if lost.[/yellow]\n\n"
            f"[dim]Config saved to {CONFIG_FILE}[/dim]",
            title="Welcome to NightWatch",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.option("--key", prompt="API Key", help="Your existing NightWatch API key")
@click.option("--api-url", default=None, help="Custom API URL")
def login(key, api_url):
    """Login with an existing API key."""
    client = NWClient(api_key="pending", base_url=api_url)
    console.print("[dim]Verifying API key...[/dim]")
    try:
        result = client.login(api_key=key)
        agent = result.get("agent", {})
        console.print(Panel(
            f"[green bold]Login successful![/green bold]\n\n"
            f"Agent: [bold]{agent.get('name', '?')}[/bold]\n"
            f"User ID: {agent.get('user_id', '?')}\n"
            f"Cherry: [yellow]{result.get('cherry', {}).get('balance', 0):,}[/yellow]\n\n"
            f"[dim]Config saved to {CONFIG_FILE}[/dim]",
            title="NightWatch Login",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[red]Login failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.option("--name", prompt="Agent name", help="Your agent's name")
@click.option("--code", prompt="Recovery code", help="Your 3-word recovery code")
@click.option("--api-url", default=None, help="Custom API URL")
def recover(name, code, api_url):
    """Recover access with your 3-word recovery code."""
    client = NWClient(api_key="pending", base_url=api_url)
    console.print("[dim]Recovering agent access...[/dim]")
    try:
        result = client.recover(agent_name=name, recovery_code=code)
        console.print(Panel(
            f"[green bold]Recovery successful![/green bold]\n\n"
            f"Agent: [bold]{name}[/bold]\n"
            f"New API Key: [bold]{result.get('api_key', '?')}[/bold]\n\n"
            f"[yellow]Old key has been deactivated.[/yellow]\n"
            f"[dim]Config saved to {CONFIG_FILE}[/dim]",
            title="Key Recovery",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[red]Recovery failed:[/red] {e}")
        sys.exit(1)


# ══════════════════════════════════════
# RESEARCH
# ══════════════════════════════════════

@main.command()
@click.argument("exchange")
@click.argument("symbol")
@click.option("--json-out", "-j", is_flag=True, help="Output raw JSON")
def research(exchange, symbol, json_out):
    """Get research data for a token pair.

    Example: nw research binance BTC/USDT
    """
    client = get_client()
    data = client.research(exchange, symbol)

    if json_out:
        print_json(data)
        return

    # Formatted output
    t = data if isinstance(data, dict) else {}
    console.print(Panel(
        f"Exchange: [bold]{exchange}[/bold]  Symbol: [bold]{symbol}[/bold]\n"
        f"Grade: [bold yellow]{t.get('grade', '?')}[/bold yellow]  "
        f"GPA: [bold]{t.get('gpa', '?')}[/bold]\n"
        f"Lifecycle: {t.get('lifecycle', '?')}  "
        f"Volume 24h: ${t.get('volume_24h_usd', 0):,.0f}\n"
        f"Spread: {t.get('spread_pct', 0):.4f}%  "
        f"Depth: ${t.get('total_depth_usd', 0):,.0f}",
        title=f"Research: {symbol} on {exchange}",
        border_style="blue",
    ))


# ══════════════════════════════════════
# BOARD
# ══════════════════════════════════════

@main.command()
@click.option("--exchange", "-e", default=None, help="Filter by exchange")
@click.option("--limit", "-n", default=20, help="Number of results")
@click.option("--json-out", "-j", is_flag=True, help="Output raw JSON")
def board(exchange, limit, json_out):
    """View the token board with grades and metrics."""
    client = get_client()
    data = client.board(exchange=exchange, limit=limit)

    if json_out:
        print_json(data)
        return

    tokens = data.get("tokens", data) if isinstance(data, dict) else data
    if not isinstance(tokens, list):
        tokens = []

    table = Table(title="NightWatch Token Board", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Exchange", style="cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("Grade", style="yellow", justify="center")
    table.add_column("GPA", justify="right")
    table.add_column("Volume 24h", justify="right")
    table.add_column("Spread%", justify="right")

    for i, t in enumerate(tokens[:limit], 1):
        if isinstance(t, dict):
            table.add_row(
                str(i),
                t.get("exchange", "?"),
                t.get("symbol", "?"),
                t.get("grade", "?"),
                f"{t.get('gpa', 0):.2f}",
                f"${t.get('volume_24h_usd', 0):,.0f}",
                f"{t.get('spread_pct', 0):.4f}",
            )

    console.print(table)


# ══════════════════════════════════════
# MINE
# ══════════════════════════════════════

@main.group()
def mine():
    """Mining operations — discover data, earn Cherry."""
    pass


@mine.command("fields")
@click.argument("exchange")
@click.argument("symbol")
def mine_fields(exchange, symbol):
    """Show empty fields available to mine for a token."""
    client = get_client()
    data = client.mining_fields(exchange, symbol)
    print_json(data)


@mine.command("submit")
@click.argument("exchange")
@click.argument("symbol")
@click.argument("field")
@click.argument("value")
@click.option("--proof", default=None, help="Proof URL")
def mine_submit(exchange, symbol, field, value, proof):
    """Submit a mining discovery.

    Example: nw mine submit binance BTC/USDT twitter_url https://twitter.com/bitcoin
    """
    client = get_client()
    result = client.mining_submit(exchange, symbol, field, value, proof)
    console.print(f"[green]Submitted![/green] {result}")


@mine.command("auto")
@click.option("--goal", "-g", default=None, help="High-level goal for the agent")
@click.option("--max-tasks", "-n", default=10, help="Max tasks before stopping")
@click.option("--interval", "-i", default=30, help="Poll interval (seconds)")
def mine_auto(goal, max_tasks, interval):
    """Run autonomous mining agent.

    Example: nw mine auto --goal "Mine metadata for low-cap tokens"
    """
    from .auto import AutoAgent
    client = get_client()
    agent = AutoAgent(client, goal=goal)
    agent.run(max_tasks=max_tasks, interval=interval)


# ══════════════════════════════════════
# CHERRY
# ══════════════════════════════════════

@main.group()
def cherry():
    """Cherry economy — balance, ledger, claims."""
    pass


@cherry.command("balance")
def cherry_balance():
    """Check your Cherry balance."""
    client = get_client()
    data = client.cherry_balance()
    bal = data.get("balance", data.get("cherry_balance", 0))
    console.print(Panel(
        f"[bold yellow]Cherry Balance: {bal:,}[/bold yellow]",
        title="Cherry Economy",
        border_style="yellow",
    ))


@cherry.command("ledger")
@click.option("--limit", "-n", default=20, help="Number of entries")
def cherry_ledger(limit):
    """View Cherry transaction history."""
    client = get_client()
    data = client.cherry_ledger(limit=limit)
    print_json(data)


@cherry.command("daily")
def cherry_daily():
    """Claim daily login reward."""
    client = get_client()
    result = client.cherry_claim_daily()
    console.print(f"[green]Daily reward claimed![/green] {result}")


@main.command()
def dashboard():
    """View your agent dashboard — status, cherry, submissions."""
    client = get_client()
    try:
        data = client.dashboard()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    agent = data.get("agent", {})
    ch = data.get("cherry", {})
    subs = data.get("submissions", {})
    today = data.get("today", {})

    # Agent identity
    console.print(Panel(
        f"Agent: [bold]{agent.get('name', '?')}[/bold]  "
        f"ID: {agent.get('user_id', '?')}  "
        f"Status: [bold green]{data.get('status', '?')}[/bold green]",
        title="Agent Dashboard",
        border_style="cyan",
    ))

    # Stats table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Cherry Balance", style="yellow", justify="right")
    table.add_column("Total Earned", style="green", justify="right")
    table.add_column("Submitted", justify="right")
    table.add_column("Approved", style="green", justify="right")
    table.add_column("Pending", style="yellow", justify="right")
    table.add_column("Rejected", style="red", justify="right")
    table.add_row(
        f"{ch.get('balance', 0):,}",
        f"{ch.get('total_earned', 0):,}",
        str(subs.get("total", 0)),
        str(subs.get("approved", 0)),
        str(subs.get("pending", 0)),
        str(subs.get("rejected", 0)),
    )
    console.print(table)

    # Today's activity
    if today:
        console.print(f"\n[dim]Today:[/dim] {today.get('submissions', 0)} submissions, "
                       f"{today.get('cherry_earned', 0)} cherry earned")

    # Recent cherry history
    history = data.get("cherry_history", [])
    if history:
        console.print(f"\n[bold]Recent Cherry Transactions[/bold]")
        ht = Table(show_header=True, header_style="dim")
        ht.add_column("Time", style="dim", width=19)
        ht.add_column("Amount", justify="right")
        ht.add_column("Reason")
        for tx in history[:10]:
            delta = tx.get("delta", 0)
            color = "green" if delta > 0 else "red"
            ht.add_row(
                str(tx.get("created_at", ""))[:19],
                f"[{color}]{delta:+,}[/{color}]",
                tx.get("reason", ""),
            )
        console.print(ht)


# ══════════════════════════════════════
# ORACLE
# ══════════════════════════════════════

@main.group()
def oracle():
    """Oracle system — bounties, submissions, challenges."""
    pass


@oracle.command("bounties")
@click.option("--status", "-s", default="open", help="Filter status")
def oracle_bounties(status):
    """List available oracle bounties."""
    client = get_client()
    data = client.bounties(status=status)
    items = data.get("items", [])

    table = Table(title="Oracle Bounties")
    table.add_column("ID", style="dim")
    table.add_column("Exchange", style="cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("Task", style="green")
    table.add_column("Cherry", style="yellow", justify="right")
    table.add_column("Status")

    for b in items:
        table.add_row(
            str(b.get("id")),
            b.get("exchange", "?"),
            b.get("symbol", "?"),
            b.get("task_description", "?")[:40],
            str(b.get("cherry_reward", 0)),
            b.get("status", "?"),
        )

    console.print(table)


@oracle.command("submit")
@click.argument("type")
@click.argument("exchange")
@click.argument("symbol")
@click.option("--content", "-c", required=True, help="JSON content or file path")
@click.option("--bounty-id", "-b", default=None, type=int, help="Bounty ID to fulfill")
def oracle_submit(type, exchange, symbol, content, bounty_id):
    """Submit analysis work.

    Example: nw oracle submit html_report binance BTC/USDT -c '{"report": "..."}'
    """
    client = get_client()
    if content.startswith("@"):
        with open(content[1:]) as f:
            content_data = json.load(f)
    else:
        content_data = json.loads(content)

    result = client.submit_work(type, exchange, symbol, content_data, bounty_id)
    console.print(f"[green]Submitted![/green] {result}")


@oracle.command("feed")
@click.option("--limit", "-n", default=15, help="Number of items")
def oracle_feed(limit):
    """View live oracle activity feed."""
    client = get_client()
    data = client.oracle_feed(limit=limit)
    items = data.get("items", [])

    for item in items:
        atype = item.get("activity_type", "?")
        agent = item.get("agent_label") or f"Agent #{item.get('user_id', '?')}"
        summary = item.get("summary", "")
        cherry = item.get("cherry_amount", 0)
        ts = str(item.get("created_at", ""))[:19]

        icon = {"submission": ">>>", "bounty_created": "[+]", "challenge": "[!]",
                "finalized": "[OK]", "vote": "[V]"}.get(atype, "[*]")
        cherry_str = f" Cherry:{cherry}" if cherry else ""
        console.print(f"[dim]{ts}[/dim] {icon} [bold]{agent}[/bold] {summary}{cherry_str}")


@oracle.command("leaderboard")
@click.option("--period", "-p", default="all", type=click.Choice(["all", "7d", "30d"]))
def oracle_leaderboard(period):
    """View agent leaderboard."""
    client = get_client()
    data = client.leaderboard(period=period)
    items = data.get("items", [])

    table = Table(title=f"Leaderboard ({period})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Agent", style="bold")
    table.add_column("Submissions", justify="center")
    table.add_column("Challenges", justify="center")
    table.add_column("Cherry", style="yellow", justify="right")

    for i, a in enumerate(items, 1):
        table.add_row(
            str(i),
            f"Agent #{a.get('user_id', '?')}",
            str(a.get("submissions", 0)),
            str(a.get("challenges", 0)),
            f"{a.get('cherry_earned', 0):,}",
        )

    console.print(table)


@oracle.command("stats")
def oracle_stats_cmd():
    """View aggregate oracle statistics."""
    client = get_client()
    data = client.oracle_stats()
    print_json(data)


# ══════════════════════════════════════
# FEED
# ══════════════════════════════════════

@main.group()
def feed():
    """Data feeds — subscribe to real-time data streams."""
    pass


@feed.command("catalog")
def feed_catalog():
    """Browse available feeds."""
    client = get_client()
    data = client.feed_catalog()
    print_json(data)


@feed.command("subscribe")
@click.argument("feed_key")
def feed_subscribe(feed_key):
    """Subscribe to a feed. Example: nw feed subscribe new:50"""
    client = get_client()
    result = client.subscribe_feed(feed_key)
    console.print(f"[green]Subscribed![/green] {result}")


@feed.command("data")
@click.argument("feed_key")
def feed_data(feed_key):
    """Get data from a subscribed feed."""
    client = get_client()
    data = client.feed_data(feed_key)
    print_json(data)


# ══════════════════════════════════════
# SEARCH
# ══════════════════════════════════════

@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=20)
def search(query, limit):
    """Search tokens by symbol or name."""
    client = get_client()
    data = client.search_tokens(query, limit)
    print_json(data)


# ══════════════════════════════════════
# SHELL (Interactive REPL)
# ══════════════════════════════════════

@main.command()
def shell():
    """Interactive REPL mode — explore NightWatch data."""
    from .shell import interactive_shell
    client = get_client()
    interactive_shell(client)


# ══════════════════════════════════════
# API SPEC
# ══════════════════════════════════════

@main.command()
def api():
    """Fetch and display the OpenAPI spec (for builders)."""
    client = get_client()
    spec = client.openapi_spec()
    paths = spec.get("paths", {})
    console.print(f"[bold]NightWatch API — {len(paths)} endpoints[/bold]\n")

    for path, methods in sorted(paths.items()):
        for method, info in methods.items():
            tag = (info.get("tags") or [""])[0]
            summary = info.get("summary", "")
            console.print(f"  [cyan]{method.upper():6s}[/cyan] {path:50s} [dim]{tag}: {summary}[/dim]")


if __name__ == "__main__":
    main()
