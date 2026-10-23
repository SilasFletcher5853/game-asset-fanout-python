from dataclasses import dataclass
from typing import Any

from infrai_client import InfraiClient


@dataclass(frozen=True)
class GameEvent:
    player_id: str
    asset_id: str
    event_type: str
    asset_url: str


def notification_targets(event: GameEvent) -> list[str]:
    """Moderation owns risky assets; ordinary assets go to followers."""
    if event.event_type == "asset.flagged":
        return ["moderation"]
    return ["followers", "activity-feed"]


def fan_out(event: GameEvent, client: InfraiClient) -> dict[str, Any]:
    targets = notification_targets(event)
    payload = {
        "event_id": f"{event.player_id}:{event.asset_id}:{event.event_type}",
        "player_id": event.player_id,
        "asset_id": event.asset_id,
        "event_type": event.event_type,
        "asset_url": event.asset_url,
        "targets": targets,
    }
    return client.publish(payload)


def drain_once(client: InfraiClient) -> list[str]:
    data = client.consume(max_messages=20, visibility_timeout=30)
    handled: list[str] = []
    for message in data.get("messages", []):
        message_id = message.get("message_id")
        if message_id:
            handled.append(message_id)
            client.ack(message_id)
    return handled


if __name__ == "__main__":
    import os

    event = GameEvent(
        player_id=os.environ.get("PLAYER_ID", "player-42"),
        asset_id=os.environ.get("ASSET_ID", "sword-7"),
        event_type=os.environ.get("EVENT_TYPE", "asset.published"),
        asset_url=os.environ.get("ASSET_URL", "https://cdn.example.test/sword-7"),
    )
    client = InfraiClient()
    print("published:", fan_out(event, client))
    print("acknowledged:", drain_once(client))
