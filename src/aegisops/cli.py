"""AegisOps CLI entrypoints."""

from __future__ import annotations

import argparse
import asyncio

from aegisops.config.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="aegisops", description="AegisOps AIOps harness")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    import uvicorn

    settings = Settings()
    uvicorn.run(
        "aegisops.api.app:create_app",
        factory=True,
        host=args.host or settings.host,
        port=args.port or settings.port,
    )


def demo_main() -> None:
    parser = argparse.ArgumentParser(prog="aegisops-demo", description="Run deterministic AegisOps demos")
    parser.add_argument("--demo", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()
    from aegisops.demo import run_demo

    asyncio.run(run_demo(args.demo, args.out))
