from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScenarioMarker:
    key: str
    label: str
    progress: float


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    version: int
    name: str
    description: str
    difficulty: str
    direction: str
    duration_seconds: float
    geometry: tuple[tuple[float, float], ...]
    markers: tuple[ScenarioMarker, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Scenario":
        direction = str(payload["direction"])
        if direction not in {"left", "right"}:
            raise ValueError("direction deve ser left ou right")

        duration = float(payload["duration_seconds"])
        if not 5.0 <= duration <= 10.0:
            raise ValueError("duration_seconds deve ficar entre 5 e 10 segundos")

        geometry = tuple(
            (float(point[0]), float(point[1])) for point in payload["geometry"]
        )
        if len(geometry) < 3:
            raise ValueError("geometry precisa de ao menos três pontos")
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in geometry):
            raise ValueError("geometry deve usar coordenadas normalizadas")

        markers = tuple(
            ScenarioMarker(
                key=str(marker["key"]),
                label=str(marker["label"]),
                progress=float(marker["progress"]),
            )
            for marker in payload["markers"]
        )
        progresses = [marker.progress for marker in markers]
        if any(not 0.0 <= progress <= 1.0 for progress in progresses):
            raise ValueError("marker progress deve ficar entre 0 e 1")
        if progresses != sorted(progresses):
            raise ValueError("markers devem estar ordenados por progresso")

        return cls(
            scenario_id=str(payload["id"]),
            version=int(payload["version"]),
            name=str(payload["name"]),
            description=str(payload["description"]),
            difficulty=str(payload["difficulty"]),
            direction=direction,
            duration_seconds=duration,
            geometry=geometry,
            markers=markers,
        )

    @classmethod
    def load(cls, path: str | Path) -> "Scenario":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    def active_marker(self, progress: float) -> ScenarioMarker:
        current = self.markers[0]
        for marker in self.markers:
            if progress < marker.progress:
                break
            current = marker
        return current
