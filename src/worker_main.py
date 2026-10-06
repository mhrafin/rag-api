import asyncio

from src.workers.worker import Worker


async def main():

    worker = Worker(poll_interval=5.0)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
