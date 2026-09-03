from pathlib import Path
import json

import pytest

from pilotagem_virtual.domain.brake_scoring import score, simulate_abs, SURFACES
from pilotagem_virtual.domain.calibration import NormalizedControls, observed_g29_profile
from pilotagem_virtual.domain.exercise import load_catalog
from pilotagem_virtual.domain.session import AttemptSample, AttemptSession
from pilotagem_virtual.persistence import TrainingStore, attempt_payload
from pilotagem_virtual.input.device import DeviceInfo


CATALOG=load_catalog(Path('resources/scenarios/brake_levels_v1.json'))


def series(exercise, brake=None, before=None, jitter=0):
    rows=[]
    for n in range(round(exercise.duration*120)):
        t=n/120
        value=exercise.value(t) if brake is None else brake(t)
        if jitter: value=max(0,min(1,value+((-1)**n)*jitter))
        if before is not None and t < exercise.windows[0][0]: value=before
        rows.append(AttemptSample(round(t*1e9),t/exercise.duration,NormalizedControls(brake=value)))
    return tuple(rows)


def test_catalog_has_eight_ordered_versioned_levels():
    assert [e.level for e in CATALOG] == list(range(1,9))
    assert {e.family for e in CATALOG} == {'hold','steps','release','curve','limit'}
    assert all(e.formula=='brake-v1' and 5 <= e.duration <= 10 for e in CATALOG)


@pytest.mark.parametrize('level',[1,2,3,4,5,6,8])
def test_perfect_brake_curve_scores_at_least_99(level):
    result=score(CATALOG[level-1],series(CATALOG[level-1]))
    assert result['valid'] and result['score'] >= 99


def test_hold_ignores_values_before_scored_window_and_weights_time():
    exercise=CATALOG[0]
    a=score(exercise,series(exercise,before=0))
    b=score(exercise,series(exercise,before=1))
    assert a['score']==b['score']==100
    poor=score(exercise,series(exercise,lambda t: 0))
    assert poor['score'] < 50 and poor['components'][0]['score']==0


def test_boundary_policy_rejects_long_edge_gap_and_ignores_opposite_outside_values():
    exercise=CATALOG[0]
    original=series(exercise,before=0)
    opposite=series(exercise,before=1)
    assert score(exercise,original)['phases']==score(exercise,opposite)['phases']
    gapped=tuple(s for s in original if not (1 <= s.elapsed_ns/1e9 < 1.04))
    result=score(exercise,gapped)
    assert not result['valid'] and 'bordas' in result['feedback']


def test_release_abrupt_and_real_reapplication_are_detected_but_noise_is_not():
    exercise=CATALOG[4]
    perfect=score(exercise,series(exercise))
    abrupt=score(exercise,series(exercise,lambda t: 1 if t<3.75 else 0))
    reapplied=score(exercise,series(exercise,lambda t: min(1,exercise.value(t)+(.12 if 3.5<t<4 else 0))))
    noisy=score(exercise,series(exercise,jitter=.005))
    assert perfect['score'] > abrupt['score']
    assert reapplied['release_metrics'][0]['reapplications'] >= 1
    assert noisy['release_metrics'][0]['reapplications']==0


def test_incomplete_acquisition_gets_no_score():
    exercise=CATALOG[1]
    result=score(exercise,series(exercise)[::3])
    assert not result['valid'] and result['score'] is None


def test_lock_model_handles_equality_recovery_multiple_and_unrecovered_end():
    points=[(1.,.8),(2.,.81),(2.2,.7),(2.5,.81),(3.,.81)]
    equal=simulate_abs([(1.,.8),(3.,.8)],SURFACES['Seca'])
    result=simulate_abs(points,SURFACES['Seca'])
    assert not equal['locks']
    assert len(result['locks'])==2 and result['locks'][0]['recovered'] and not result['locks'][1]['recovered']
    assert result['locked_seconds'] > 0 and None in result['recovery_seconds']

    variable=simulate_abs([(0.,.7),(8.,.7)],SURFACES['Variável'])
    assert variable==simulate_abs([(0.,.7),(8.,.7)],SURFACES['Variável'])
    assert variable['locks']


def test_persistence_profile_and_immutable_idempotent_attempt(tmp_path):
    store=TrainingStore(tmp_path/'app.db')
    info=DeviceInfo('x','G29','guid',4,0,0)
    profile=observed_g29_profile(info.name,info.guid)
    store.save_profile(info,profile)
    assert store.load_profile(info)==profile
    exercise=CATALOG[0]
    session=AttemptSession(__import__('pilotagem_virtual.domain.scenario',fromlist=['Scenario']).Scenario(
        exercise.id,1,exercise.name,exercise.objective,'1','right',exercise.duration,((0,0),(1,0),(1,1)),()))
    session.start(0,profile)
    for row in series(exercise): session.tick(3_000_000_000+row.elapsed_ns,row.controls)
    session.tick(3_000_000_000+round(exercise.duration*1e9),NormalizedControls())
    result=score(exercise,session.snapshot().samples)
    payload=attempt_payload(session.snapshot(),exercise,result,'Guiado','Seca',False,None)
    store.save_attempt(payload); store.save_attempt(payload)
    changed=json.loads(json.dumps(payload)); changed['mode']='Avaliação'
    with pytest.raises(ValueError): store.save_attempt(changed)
