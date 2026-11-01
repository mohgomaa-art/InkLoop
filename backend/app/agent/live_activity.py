"""Short-lived live tool activity for the Agent chat progress UI.

The durable transcript remains the source of truth after a turn completes. This
store only lets the browser observe real tool dispatches while the chat request
is still running.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict
import time

_lock = Lock()
_activities: Dict[str, Dict[str, Any]] = {}


def begin_activity(activity_id: str) -> None:
    with _lock:
        now = time.time()
        for key, value in list(_activities.items()):
            if now - value.get("updated_at", now) > 3600:
                _activities.pop(key, None)
        while len(_activities) >= 256:
            oldest = min(_activities, key=lambda key: _activities[key].get("updated_at", 0))
            _activities.pop(oldest, None)
        _activities[activity_id] = {"tools": [], "production_job": None, "finished": False, "updated_at": now}


def record_tool_activity(activity_id: str, event: Dict[str, Any]) -> None:
    with _lock:
        activity = _activities.setdefault(activity_id, {"tools": [], "production_job": None, "finished": False})
        activity["updated_at"] = time.time()
        if isinstance(event.get("production_job"), dict):
            activity["production_job"] = dict(event["production_job"])
            return
        tools = activity["tools"]
        for index, current in enumerate(tools):
            if current.get("call_id") == event.get("call_id"):
                tools[index] = {**current, **event}
                break
        else:
            tools.append(dict(event))


def finish_activity(activity_id: str) -> None:
    with _lock:
        activity = _activities.setdefault(activity_id, {"tools": [], "production_job": None, "finished": False})
        activity["finished"] = True
        activity["updated_at"] = time.time()


def get_activity(activity_id: str) -> Dict[str, Any]:
    with _lock:
        activity = _activities.get(activity_id)
        if not activity:
            return {"tools": [], "production_job": None, "finished": False}
        return {
            "tools": [dict(item) for item in activity["tools"]],
            "production_job": dict(activity["production_job"]) if activity.get("production_job") else None,
            "finished": activity["finished"],
        }
