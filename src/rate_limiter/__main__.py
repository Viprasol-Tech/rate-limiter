"""Module entry point so ``python -m rate_limiter`` runs the CLI.

Part of Rate Limiter by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from rate_limiter.cli import app

if __name__ == "__main__":
    app()
