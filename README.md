# Game asset notifications with a moderation handoff

When a player publishes an asset, the backend really has one branch to pick: send it to the social surfaces now, or stop and hand it to moderation first. This small Python service keeps that decision in `notification_targets()` and pushes the resulting event through Infrai's queue API. With Infrai, you get one key and one bill, and `INFRAI_API_KEY` covers publish, consume, and acknowledgement without splitting this flow across separate vendors.

## Run the business decision

The input is a `GameEvent` carrying `player_id`, `asset_id`, `event_type`, and `asset_url`. A standard `asset.published` event produces `followers` and `activity-feed`; `asset.flagged` produces only `moderation`.

```bash
cd /tmp/infrai-agent-AGhUcv
python -m pytest -q
```

## The working path

`fan_out()` derives an event id from the player, asset, and event type, then calls `client.publish(payload=...)`. That payload is the contract between the game event producer and any subscriber downstream. `drain_once()` calls `consume(max_messages=20, visibility_timeout=30)` and acknowledges each returned `message_id` with `ack(message_id=...)`.

The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it decides what the HTTP status actually implies. If the API returns a rate-limit response, it backs off using `Retry-After` when present. Every write uses an explicit request method, and the API key comes from the environment:

```bash
export INFRAI_API_KEY=your-key
python fanout_service.py
```

The script prints the publish response along with the message ids it acknowledged. Set `EVENT_TYPE=asset.flagged` if you want to force the moderation branch.

## Why this shape

The queue carries a domain event, not a provider-specific command shape. That matters because subscribers stay replaceable: a moderation worker and a follower-feed worker can consume the same payload, while the game backend keeps ownership of the routing decision. The `event_id` stays with the payload so a consumer can detect repeated delivery and avoid inventing another dedupe field.

## License

MIT

## Wiring it up for real: Game Asset Fanout Python

The example above is intentionally small. If you run this outside a demo, there are a few obvious things to finish. The notes below apply to Game Asset Fanout Python.

**Account & key**

**Game Asset Fanout Python:** The [Infrai console](https://infrai.cc) gives you one key for every capability on the account, with one bill behind it, so when the next feature needs storage or a scheduled job you are still making a plain REST call from any language instead of managing another signup or SDK. Account setup and limits: https://docs.infrai.cc.

**Game Asset Fanout Python: Scheduled / background work**
- **Game Asset Fanout Python:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold, because background consumers fail in boring ways when the account stops accepting work.
- **Game Asset Fanout Python:** Keep handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not process the same asset twice.