import asyncio

from src.database import get_session


class Worker:
    def __init__(self, poll_interval: float = 1.0):

        self.poll_interval = poll_interval

    async def start(self):
        session = get_session()
        while True:
            print("Hello I am worker")
            await asyncio.sleep(self.poll_interval)
