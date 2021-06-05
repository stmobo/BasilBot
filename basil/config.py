from __future__ import annotations

import json
from pathlib import Path
import os
import typing
from typing import Any, Set, Dict


class Config:
    config_file: Path
    static_manifest: Dict[str, Dict[str, str]]

    discord_log: Path
    static_manifest_path: Path

    token: str
    cookie_signer_key: str
    client_id: str
    client_secret: str

    primary_redis_url: str
    api_base_url: str
    oauth2_redirect_uri: str
    login_redirect_target: str

    summon_prefix: str
    management_role_name: str
    primary_server_id: int

    maintenance_mode: bool
    dev_mode: bool
    administrators: Set[int]

    def __init__(self):
        self.config_file = Path(os.environ["BASIL_CONFIG"]).resolve()
        self.load()

    @classmethod
    def instance(cls) -> Config:
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @classmethod
    def get(cls, name: str, default: Any) -> Any:
        return cls.instance()._config.get(name, default)

    @property
    def as_dict(self) -> Dict[str, Any]:
        ret = {}

        for attr, hint in Config.__annotations__.items():
            if attr == "_inst" or attr == "config_file":
                continue

            origin = typing.get_origin(hint)
            val = getattr(self, attr)

            if origin is set:
                val = list(val)
            elif hint == "Path":
                val = str(val)

            ret[attr] = val

        return ret

    def load(self):
        self.config_file = Path(os.environ["BASIL_CONFIG"]).resolve()

        with self.config_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

            for attr, hint in Config.__annotations__.items():
                if (
                    attr == "_inst"
                    or attr == "config_file"
                    or attr == "static_manifest"
                ):
                    continue

                origin = typing.get_origin(hint)
                type_args = typing.get_args(hint)
                val = data[attr]

                if origin is set:
                    val = set(map(type_args[0], val))
                elif origin is not None:
                    val = origin(val)
                elif hint == "str":
                    val = str(val).strip()
                elif hint == "Path":
                    val = Path(val).resolve()

                setattr(self, attr, val)

        with self.static_manifest_path.open("r", encoding="utf-8") as f:
            self.static_manifest = json.load(f)

    def save(self):
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(self.as_dict, f, indent=4)


config: Config = Config()
