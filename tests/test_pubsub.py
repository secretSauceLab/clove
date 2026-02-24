import pytest
from app.pubsub import LocalPubSub
import asyncio

@pytest.mark.asyncio
async def test_publish_reaches_subscriber():
    pubsub = LocalPubSub()
    pubsub.create_topic("test-topic")

    received = []

    async def handler(message):
        received.append(message)

    pubsub.subscribe("test-topic", handler)
    await pubsub.publish("test-topic", {"hello": "world"})

@pytest.mark.asyncio
async def test_fan_out():
    pubsub = LocalPubSub()
    pubsub.create_topic("test-topic")

    receivedA = []
    receivedB = []

    async def handlerA(message):
        receivedA.append(message)

    async def handlerB(message):
        receivedB.append(message)

    pubsub.subscribe("test-topic", handlerA)
    pubsub.subscribe("test-topic", handlerB)

    await pubsub.publish("test-topic", {"hello": "world"})
    await asyncio.sleep(0.1)

    assert len(receivedA) == 1
    assert len(receivedB) == 1