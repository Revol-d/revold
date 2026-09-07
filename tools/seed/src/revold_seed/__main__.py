"""Ponto de entrada de `python -m revold_seed` — ver `make seed`."""
from __future__ import annotations

import asyncio

from revold_seed.runner import run_seed

if __name__ == "__main__":
    asyncio.run(run_seed())
