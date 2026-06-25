"""Load the single project config (config.yaml) and resolve paths."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


def project_root() -> Path:
    """Repo root = first parent containing config.yaml."""
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "config.yaml").exists():
            return p
    raise FileNotFoundError("config.yaml not found above " + str(here))


@dataclass(frozen=True)
class Config:
    raw: dict
    root: Path

    def path(self, key: str) -> Path:
        """Resolve a paths.<key> entry to an absolute path under the repo root."""
        rel = self.raw["paths"][key]
        return (self.root / rel).resolve()

    def __getitem__(self, key: str):
        return self.raw[key]


@lru_cache(maxsize=1)
def load_config() -> Config:
    root = project_root()
    with open(root / "config.yaml", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw=raw, root=root)
