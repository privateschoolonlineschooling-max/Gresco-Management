import json
import os
from datetime import datetime

class DataManager:
    """Simple JSON-backed storage for moderation actions."""

    def __init__(self, filename: str = "data.json"):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self) -> dict:
        if not os.path.exists(self.filename):
            return {"warnings": {}, "timeouts": {}, "bans": {}, "actions": {}}

        with open(self.filename, "r", encoding="utf-8") as file:
            return json.load(file)

    def save(self) -> None:
        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2)

    def _user_key(self, user_id: int) -> str:
        return str(user_id)

    def _ensure_user(self, user_id: int) -> str:
        key = self._user_key(user_id)
        for category in ("warnings", "timeouts", "bans", "actions"):
            self.data.setdefault(category, {})
            self.data[category].setdefault(key, [])
        return key

    def add_warning(self, user, moderator: str, reason: str) -> dict:
        key = self._ensure_user(user.id)
        entry = {
            "moderator": moderator,
            "reason": reason,
            "date": datetime.utcnow().isoformat() + "Z",
        }
        self.data["warnings"][key].append(entry)
        self.data["actions"][key].append({"type": "warning", **entry})
        self.save()
        return entry

    def add_timeout(self, user, moderator: str, reason: str, duration: str) -> dict:
        key = self._ensure_user(user.id)
        entry = {
            "moderator": moderator,
            "reason": reason,
            "duration": duration,
            "date": datetime.utcnow().isoformat() + "Z",
        }
        self.data["timeouts"][key].append(entry)
        self.data["actions"][key].append({"type": "timeout", **entry})
        self.save()
        return entry

    def add_ban(self, user, moderator: str, reason: str) -> dict:
        key = self._ensure_user(user.id)
        entry = {
            "moderator": moderator,
            "reason": reason,
            "date": datetime.utcnow().isoformat() + "Z",
        }
        self.data["bans"][key].append(entry)
        self.data["actions"][key].append({"type": "ban", **entry})
        self.save()
        return entry

    def get_user_actions(self, user) -> dict:
        key = self._user_key(user.id)
        return {
            "warnings": self.data.get("warnings", {}).get(key, []),
            "timeouts": self.data.get("timeouts", {}).get(key, []),
            "bans": self.data.get("bans", {}).get(key, []),
            "actions": self.data.get("actions", {}).get(key, []),
        }
