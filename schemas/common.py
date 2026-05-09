from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    def to_state_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")
