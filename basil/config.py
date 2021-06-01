from __future__ import annotations

import json
from pathlib import Path
import os
from typing import Optional, Any


class Config(object):
    _inst: Optional[Config] = None

    def __init__(self):
        self.config_file = Path(os.environ["BASIL_CONFIG"]).resolve()
        self._config = {
            "token": "",
            "primary_redis_url": "redis://localhost:6379/0",
            "summon_prefix": "b!",
            "maintenance_mode": False,
            "management_role_name": "snippet manager",
            "discord_log": Path("/var/log/basil/discord.log"),
            "primary_server_id": 783787827061063710,
            "api_base_url": "http://127.0.0.1/",
            "oauth2_redirect_uri": "http://127.0.0.1/api/auth/authorized",
            "client_id": "",
            "client_secret": "",
            "cookie_signer_key": "",
            "login_redirect_target": "/series_index.html",
            "dev_mode": False,
        }

        self.load()

    @classmethod
    def instance(cls) -> Config:
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @classmethod
    def get(cls, name: str, default: Any) -> Any:
        return cls.instance()._config.get(name, default)

    def load(self):
        self.config_file = Path(os.environ["BASIL_CONFIG"]).resolve()

        with self.config_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

            data["token"] = data["token"].strip()
            data["discord_log"] = Path(data["discord_log"]).resolve()

            self._config.update(data)

    def save(self):
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def __getattr__(self, name):
        return self._config[name]

    def __setattr__(self, name, value):
        if name == "_config" or name == "config_file":
            object.__setattr__(self, name, value)
        else:
            self._config[name] = value
            self.save()

    def __delattr__(self, name):
        del self._config[name]
        self.save()

    def __dir__(self):
        return list(self.config.keys())


def get() -> Config:
    return Config.instance()
