from fanout_service import GameEvent, notification_targets


def test_flagged_asset_only_enters_moderation_queue():
    event = GameEvent("p1", "a9", "asset.flagged", "https://cdn.example/a9")
    assert notification_targets(event) == ["moderation"]


def test_published_asset_reaches_player_surfaces():
    event = GameEvent("p1", "a9", "asset.published", "https://cdn.example/a9")
    assert notification_targets(event) == ["followers", "activity-feed"]
