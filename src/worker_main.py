import asyncio

from src.config import get_settings
from src.workers.worker import Worker


async def main():
    settings = get_settings()
    worker = Worker(poll_interval=settings.worker_poll_interval)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
