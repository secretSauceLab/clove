import asyncio


class LocalPubSub:
    def __init__(self):
        self.topics = {}

    def create_topic(self, topic_name):
        if topic_name not in self.topics:
            self.topics[topic_name] = []

    async def publish(self, topic_name, data):
        if topic_name not in self.topics:
            raise ValueError(f"Topic '{topic_name}' does not exist")
        for q in self.topics[topic_name]:
            await q.put(data)

    def subscribe(self, topic_name, handler):
        q = asyncio.Queue()
        self.topics[topic_name].append(q)

        async def _listen():
            while True:
                message = await q.get()
                await handler(message)

        asyncio.create_task(_listen())