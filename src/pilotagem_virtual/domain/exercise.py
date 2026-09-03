"""Versioned exercise data; no dependency on acquisition or presentation."""
from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path


def interpolate(points, t):
    i = max(0, min(len(points) - 2, bisect_right(points, (t, float('inf'))) - 1))
    a, b = points[i], points[i + 1]
    f = max(0., min(1., (t - a[0]) / (b[0] - a[0])))
    return a[1] + (b[1] - a[1]) * f


@dataclass(frozen=True)
class Exercise:
    id: str
    level: int
    name: str
    objective: str
    family: str
    duration: float
    target: tuple
    windows: tuple
    tolerance: float = .05
    steering: tuple = ((0., 0.), (10., 0.))
    accelerator: tuple = ((0., 0.), (10., 0.))
    version: int = 1
    formula: str = "brake-v1"
    modes: tuple = ("Guiado", "Memória", "Avaliação")

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        for key in ('target', 'windows', 'steering', 'accelerator'):
            if key in data:
                data[key] = tuple(tuple(float(v) for v in p) for p in data[key])
        if 'modes' in data:
            data['modes'] = tuple(data['modes'])
        item = cls(**data)
        if item.family not in ('hold', 'steps', 'release', 'curve', 'limit') or not 5 <= item.duration <= 10:
            raise ValueError("Família ou duração inválida")
        if item.formula != 'brake-v1' or not 0 < item.tolerance <= .2 or not 1 <= item.level <= 8:
            raise ValueError("Parâmetros do exercício inválidos")
        for points in (item.target, item.steering, item.accelerator):
            if len(points) < 2 or points[0][0] != 0 or points[-1][0] < item.duration:
                raise ValueError("Keyframes devem cobrir o exercício")
            if any(not math.isfinite(v) for p in points for v in p) or any(b[0] <= a[0] for a, b in zip(points, points[1:])):
                raise ValueError("Keyframes inválidos")
            if any(not 0 <= p[1] <= 1 for p in points):
                raise ValueError("Alvo fora da faixa")
        if not item.windows or any(not 0 <= a < b <= item.duration for a, b in item.windows):
            raise ValueError("Janela inválida")
        if not item.modes or any(m not in ('Guiado', 'Memória', 'Avaliação') for m in item.modes):
            raise ValueError("Modo inválido")
        return item

    def value(self, t):
        return interpolate(self.target, t)


def load_catalog(path: Path):
    items = tuple(Exercise.from_dict(d) for d in json.loads(path.read_text(encoding='utf-8')))
    if sorted(e.level for e in items) != list(range(1, 9)) or len({e.id for e in items}) != 8:
        raise ValueError("Catálogo precisa dos oito níveis")
    return items
