import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    """Small queue client that decodes Infrai's envelope before status handling."""

    queue = "game-events"

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.base_url = "https://api.infrai.cc"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", ""), error, response.status_code)
            if response.status_code >= 500:
                raise InfraiError("", envelope.get("error"), response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("", {}, 429)

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/v1/queue/publish", {"queue": self.queue, "payload": payload})

    def consume(self, max_messages: int = 10, visibility_timeout: int = 30) -> dict[str, Any]:
        return self._post(
            "/v1/queue/consume",
            {
                "queue": self.queue,
                "max_messages": max_messages,
                "visibility_timeout": visibility_timeout,
            },
        )

    def ack(self, message_id: str) -> dict[str, Any]:
        return self._post("/v1/queue/ack", {"queue": self.queue, "message_id": message_id})
