import argparse
import asyncio

import uvicorn

from app.api import create_app
from app.bot import run_bot
from app.config import get_settings
from app.db import init_database
from app.worker import run_worker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Сервис обработки фотографий")
    parser.add_argument("command", choices=["api", "bot", "worker", "init-db"])
    return parser


async def run_command(command: str) -> None:
    if command == "api":
        app = create_app()
        config = get_settings()
        server = uvicorn.Server(
            uvicorn.Config(
                app=app,
                host=config.api_host,
                port=config.api_port,
                log_level="info",
            )
        )
        await server.serve()
        return

    if command == "bot":
        await run_bot()
        return

    if command == "worker":
        await run_worker()
        return

    if command == "init-db":
        await init_database()
        return

    raise ValueError(f"Неизвестная команда: {command}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(run_command(args.command))


if __name__ == "__main__":
    main()
