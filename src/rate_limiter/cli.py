"""Command-line interface for Rate Limiter.

``rate-limiter demo`` hammers a limiter with a burst of requests on a fake
clock and reports how many were allowed vs denied — no real sleeping, fully
deterministic.

Part of Rate Limiter by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.console import Console
from rich.table import Table

from rate_limiter import __version__
from rate_limiter.clock import FakeClock
from rate_limiter.sliding_window import SlidingWindowLimiter
from rate_limiter.token_bucket import TokenBucket

app = typer.Typer(add_completion=False, help="Rate Limiter — by Viprasol Tech.")
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"rate-limiter [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def demo(
    limiter: str = typer.Option("token", help="token | sliding"),
    requests: int = typer.Option(20, help="number of requests to attempt"),
    tick: float = typer.Option(0.1, help="seconds the clock advances between requests"),
) -> None:
    """Hammer a limiter on a fake clock and show allowed/denied counts.

    The token bucket is sized capacity=5, refill=2/s; the sliding window allows
    5 requests per 1s. With the default ``tick`` of 0.1s the clock advances a
    little between each request, so a steady trickle of refills/evictions lets
    some later requests through after the initial burst is exhausted.
    """
    clock = FakeClock()
    decide: Callable[[], bool]
    if limiter == "token":
        bucket = TokenBucket(capacity=5, refill_rate=2.0, clock=clock)
        decide = bucket.try_acquire
    elif limiter == "sliding":
        window = SlidingWindowLimiter(max_requests=5, window_seconds=1.0, clock=clock)
        decide = window.try_acquire
    else:
        console.print("[red]limiter must be 'token' or 'sliding'[/]")
        raise typer.Exit(code=1)

    allowed = 0
    denied = 0
    table = Table(title=f"{limiter} limiter - {requests} requests, {tick:g}s tick")
    table.add_column("#", justify="right")
    table.add_column("t (s)", justify="right")
    table.add_column("result")

    for i in range(1, requests + 1):
        ok = decide()
        if ok:
            allowed += 1
        else:
            denied += 1
        verdict = "[green]ALLOW[/]" if ok else "[red]DENY[/]"
        table.add_row(str(i), f"{clock():.2f}", verdict)
        clock.advance(tick)

    console.print(table)
    console.print(f"Limiter: [bold]{limiter}[/]")
    console.print(f"Allowed: [bold green]{allowed}[/]   Denied: [bold red]{denied}[/]")


if __name__ == "__main__":
    app()
