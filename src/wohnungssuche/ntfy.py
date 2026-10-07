"""Push notifications via ntfy (free app for iOS/Android, no account needed)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_SERVER = "https://ntfy.sh"
MAX_MESSAGE_CHARS = 3500


@dataclass
class PushMessage:
    title: str
    message: str
    priority: int = 3                       # 1 (min) … 5 (max)
    tags: list[str] = field(default_factory=list)
    click: str | None = None                # opened when tapping the notification
    attach: str | None = None               # image URL shown in the notification
    actions: list[tuple[str, str]] = field(default_factory=list)  # (label, url)
    deliver_at: datetime | None = None      # scheduled delivery (ntfy keeps it until then)


class NtfyClient:
    def __init__(self, topic: str | None, server: str = DEFAULT_SERVER, token: str | None = None) -> None:
        self.topic = topic
        self.server = server.rstrip("/")
        self.token = token

    @property
    def enabled(self) -> bool:
        return bool(self.topic)

    def send(self, msg: PushMessage) -> None:
        payload = build_payload(self.topic or "", msg)
        if not self.enabled:
            log.info("[dry-run] would push:\n%s", json.dumps(payload, ensure_ascii=False, indent=1))
            return
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        response = requests.post(self.server, data=json.dumps(payload).encode(), headers=headers, timeout=30)
        response.raise_for_status()


def build_payload(topic: str, msg: PushMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topic": topic,
        "title": msg.title,
        "message": msg.message[:MAX_MESSAGE_CHARS],
        "priority": msg.priority,
    }
    if msg.tags:
        payload["tags"] = msg.tags
    if msg.click:
        payload["click"] = msg.click
    if msg.attach:
        payload["attach"] = msg.attach
    if msg.actions:
        payload["actions"] = [
            {"action": "view", "label": label, "url": url, "clear": False} for label, url in msg.actions[:3]
        ]
    if msg.deliver_at:
        payload["delay"] = str(int(msg.deliver_at.timestamp()))
    return payload
