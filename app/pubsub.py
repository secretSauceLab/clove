import asyncio

class PubSubMessage:
    def __init__(self, data):
        self.data = data

class LocalPubSub:
    def __init__(self):
        self.topics = {}

    def create_topic(self, topic_name):
        if topic_name not in self.topics:
            self.topics[topic_name] = []

    async def publish(self, topic_name, data):
        if topic_name not in self.topics:
            raise ValueError(f"Topic '{topic_name}' does not exist")
        message = PubSubMessage(data)
        for q in self.topics[topic_name]:
            await q.put(message)

    def subscribe(self, topic_name, handler):
        q = asyncio.Queue()
        self.topics[topic_name].append(q)

        async def _listen():
            while True:
                message = await q.get()
                await handler(message)

        asyncio.create_task(_listen())

_instance = None


def get_pubsub():
    global _instance
    if _instance is None:
        _instance = LocalPubSub()
    return _instance