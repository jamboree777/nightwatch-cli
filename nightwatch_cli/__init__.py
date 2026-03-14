"""
NightWatch CLI & SDK — Intelligence Layer for Token Analysts.

Usage as SDK:
    from nightwatch_cli import NWClient

    client = NWClient(api_key="your-key")
    research = client.research("binance", "BTC/USDT")
    print(research["grade"], research["gpa"])

Usage as CLI:
    $ nw init                    # Register & get API key
    $ nw research binance BTC    # Token research
    $ nw mine --auto             # Auto-mine Cherry
    $ nw shell                   # Interactive REPL
"""

__version__ = "0.1.0"

from .client import NWClient

__all__ = ["NWClient", "__version__"]
