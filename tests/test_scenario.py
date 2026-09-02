from __future__ import annotations

import json

import pytest

from pilotagem_virtual.domain.scenario import Scenario


def scenario_payload() -> dict:
    return {
        "id": "test",
        "version": 1,
        "name": "Teste",
        "description": "Cenário de teste",
        "difficulty": "Iniciante",
        "direction": "right",
        "duration_seconds": 8,
        "geometry": [[0.0, 0.5], [0.5, 0.5], [0.8, 0.2]],
        "markers": [
            {"key": "start", "label": "INÍCIO", "progress": 0.0},
            {"key": "braking", "label": "FREAR", "progress": 0.2},
            {"key": "apex", "label": "ÁPICE", "progress": 0.7},
        ],
    }


def test_scenario_load_and_active_marker(tmp_path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario_payload()), encoding="utf-8")

    scenario = Scenario.load(path)

    assert scenario.duration_seconds == 8
    assert scenario.active_marker(0.1).key == "start"
    assert scenario.active_marker(0.5).key == "braking"
    assert scenario.active_marker(0.9).key == "apex"


def test_scenario_rejects_duration_outside_mvp_range() -> None:
    payload = scenario_payload()
    payload["duration_seconds"] = 12

    with pytest.raises(ValueError, match="entre 5 e 10"):
        Scenario.from_dict(payload)
