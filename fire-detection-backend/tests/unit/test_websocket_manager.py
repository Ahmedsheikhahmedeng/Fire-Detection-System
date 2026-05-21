import pytest

from app.websocket.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self, fail_accept=False, fail_send=False):
        self.accepted = False
        self.messages = []
        self.fail_accept = fail_accept
        self.fail_send = fail_send

    async def accept(self):
        if self.fail_accept:
            raise RuntimeError("accept failed")
        self.accepted = True

    async def send_json(self, data):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.messages.append(data)


@pytest.mark.asyncio
async def test_connect_accepts_websocket():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)

    assert ws.accepted is True
    assert manager.connection_count() == 1


@pytest.mark.asyncio
async def test_duplicate_connection_added_only_once():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)
    await manager.connect(ws)

    assert manager.connection_count() == 1


@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)
    assert manager.connection_count() == 1

    manager.disconnect(ws)

    assert manager.connection_count() == 0


@pytest.mark.asyncio
async def test_disconnect_unknown_connection_does_not_crash():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    manager.disconnect(ws)

    assert manager.connection_count() == 0


@pytest.mark.asyncio
async def test_broadcast_sends_message_to_all_connections():
    manager = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.broadcast({"type": "TEST_EVENT", "value": 123})

    assert ws1.messages == [{"type": "TEST_EVENT", "value": 123}]
    assert ws2.messages == [{"type": "TEST_EVENT", "value": 123}]
    assert manager.connection_count() == 2


@pytest.mark.asyncio
async def test_broadcast_removes_broken_connection():
    manager = ConnectionManager()
    good_ws = FakeWebSocket()
    bad_ws = FakeWebSocket(fail_send=True)

    await manager.connect(good_ws)
    await manager.connect(bad_ws)

    await manager.broadcast({"type": "TEST_EVENT"})

    assert good_ws.messages == [{"type": "TEST_EVENT"}]
    assert manager.connection_count() == 1


@pytest.mark.asyncio
async def test_broadcast_with_no_connections_does_not_crash():
    manager = ConnectionManager()

    await manager.broadcast({"type": "NO_CLIENTS"})

    assert manager.connection_count() == 0


def test_broadcast_threadsafe_without_connections_returns_none():
    manager = ConnectionManager()

    result = manager.broadcast_threadsafe({"type": "TEST"})

    assert result is None


@pytest.mark.asyncio
async def test_broadcast_threadsafe_with_closed_loop_returns_none(monkeypatch):
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)

    class FakeClosedLoop:
        def is_closed(self):
            return True

    manager.loop = FakeClosedLoop()

    result = manager.broadcast_threadsafe({"type": "TEST"})

    assert result is None


@pytest.mark.asyncio
async def test_connection_count_returns_active_connection_count():
    manager = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    assert manager.connection_count() == 0

    await manager.connect(ws1)
    assert manager.connection_count() == 1

    await manager.connect(ws2)
    assert manager.connection_count() == 2

    manager.disconnect(ws1)
    assert manager.connection_count() == 1

    manager.disconnect(ws2)
    assert manager.connection_count() == 0
