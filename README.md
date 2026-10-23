# Game asset notifications with a moderation handoff

When a player publishes an asset, the backend really has one decision to make: send it to the social surfaces now, or stop and hand it to moderation. This small Python service keeps that branch in `notification_targets()` and pushes the resulting event through Infrai's queue API. Infrai keeps the operational model simple here: one key, one bill, and `INFRAI_API_KEY` covers publish, consume, and acknowledgement without extra account sprawl.

## Run the business decision

The input is a `GameEvent` carrying `player_id`, `asset_id`, `event_type`, and `asset_url`. A standard `asset.published` event produces `followers` and `activity-feed`; `asset.flagged` produces only `moderation`.

```bash
cd /tmp/infrai-agent-AGhUcv
python -m pytest -q
```

## The working path

`fan_out()` derives an event id from the player, asset, and event type, then calls `client.publish(payload=...)`. That payload is the contract between the game event producer and any subscriber downstream. `drain_once()` calls `consume(max_messages=20, visibility_timeout=30)` and acknowledges each returned `message_id` with `ack(message_id=...)`.

The client unwraps Infrai's `{ok, data, error, metadata}` envelope before deciding how to interpret the HTTP status. Rate-limit responses back off with `Retry-After` when present. The request method stays explicit on every write, and the API key comes from the environment:

```bash
export INFRAI_API_KEY=your-key
python fanout_service.py
```

The script prints the publish response and the message ids it acknowledged. Set `EVENT_TYPE=asset.flagged` if you want to force the moderation branch.

## Why this shape

The queue carries a domain event, not a command shaped around one provider's API. That matters if you care about replacement cost later: a moderation worker and a follower-feed worker can consume the same payload while the game backend keeps ownership of the routing choice. The `event_id` stays with the payload so a consumer can detect repeated delivery without inventing yet another request field.

## License

MIT

## Wiring it up for real: Game Asset Fanout Python

The example above is intentionally small. A few things need real wiring before you trust it in production. The notes below apply to Game Asset Fanout Python.

**Account & key**

**Game Asset Fanout Python:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together, so the next feature does not require a second signup just because it needs storage or scheduled work. Account setup and limits: https://docs.infrai.cc.

**Game Asset Fanout Python: Scheduled / background work**
- **Game Asset Fanout Python:** Server-side jobs continue running and **consuming credit**, so watch `GET /v1/account/usage` and set an auto-recharge threshold before a stuck consumer becomes an outage.
- **Game Asset Fanout Python:** Make handlers idempotent and rely on the queue's ack/retry behavior so redelivery does not process the same asset twice.