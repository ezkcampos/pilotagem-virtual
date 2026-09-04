"""Pure scoring v1. Originals stay intact; only event analysis uses a 120 Hz grid."""
from __future__ import annotations

import math
from dataclasses import asdict
from pilotagem_virtual.domain.acquisition import summarize_acquisition
from pilotagem_virtual.domain.exercise import interpolate


FORMULA = {
    'version': 'brake-v1', 'boundary': 'inside-endpoint-hold-max-25ms-v1',
    'minimum_hz': 60, 'maximum_gap_ms': 50, 'grid_hz': 120,
    'acquisition_dwell_s': .2, 'reapplication_amplitude': .03,
    'smoothing_radius': 3, 'error_scale': .3, 'stability_scale': .15,
    'rate_scale': 2., 'timing_scale_s': 1.5,
    'weights': {'hold': [40, 25, 20, 15], 'steps': [30, 30, 20, 20],
                'release': [40, 25, 20, 15], 'curve': [40, 25, 20, 15],
                'limit': [45, 25, 20, 10], 'custom': [45, 25, 20, 10]},
}
SURFACES = {
    'Seca': ((0., .8), (10., .8)), 'Molhada': ((0., .6), (10., .6)),
    'Escorregadia': ((0., .4), (10., .4)),
    'Variável': ((0., .8), (3., .8), (4., .55), (6., .55), (7., .75), (10., .75)),
}
MODEL = {'version': 'didactic-abs-v1', 'step_hz': 120, 'recovery_margin': .03, 'recovery_dwell_s': .1}


def window_series(samples, start, end, channel='brake'):
    """Only readings INSIDE the window; bounded endpoint hold is explicit v1 policy.

    At most 25 ms of each edge is estimated from its nearest inside reading.
    This keeps pre-window data invariant, without pretending edges were acquired.
    """
    values = [(s.elapsed_ns / 1e9, getattr(s.controls, channel)) for s in samples
              if start <= s.elapsed_ns / 1e9 <= end]
    if len(values) < 2 or values[0][0] - start > .025 or end - values[-1][0] > .025:
        raise ValueError('Cobertura insuficiente nas bordas da fase')
    estimated = (values[0][0] - start) + (end - values[-1][0])
    if values[0][0] > start:
        values.insert(0, (start, values[0][1]))
    if values[-1][0] < end:
        values.append((end, values[-1][1]))
    return values, estimated


def phase_metrics(series, target, tolerance):
    start, end = series[0][0], series[-1][0]
    knots = sorted({t for t, _ in series} | {t for t, _ in target if start < t < end})
    split = [knots[0]]
    for a, b in zip(knots, knots[1:]):
        ea = interpolate(series, a) - interpolate(target, a)
        eb = interpolate(series, b) - interpolate(target, b)
        crossings = [a + (b-a)*(c-ea)/(eb-ea) for c in (-tolerance, 0., tolerance)
                     if ea != eb and min(ea, eb) < c < max(ea, eb)]
        split.extend(sorted(crossings))
        split.append(b)
    inside = error = square = mean = 0.
    dwell_start = None
    acquisition = end - start
    acquired = False
    for a, b in zip(split, split[1:]):
        ea = interpolate(series, a) - interpolate(target, a)
        eb = interpolate(series, b) - interpolate(target, b)
        dt = b-a
        mean += dt*(ea+eb)/2
        error += dt*(abs(ea)+abs(eb))/2
        square += dt*(ea*ea+ea*eb+eb*eb)/3
        if abs((ea+eb)/2) <= tolerance + 1e-10:
            inside += dt
            if dwell_start is None:
                dwell_start = a
            if not acquired and b-dwell_start >= .2 - 1e-10:
                acquisition, acquired = dwell_start-start, True
        else:
            dwell_start = None
    duration = end-start
    return {'in_band': inside/duration, 'mae': error/duration,
            'stability': math.sqrt(max(0., square/duration-(mean/duration)**2)),
            'acquisition': acquisition, 'acquired': acquired,
            'overshoot': max(0., max(interpolate(series, t)-interpolate(target, t) for t in split))}


def derived_grid(series):
    start, end = series[0][0], series[-1][0]
    # Phase-relative integer grid, nearest-nanosecond conversion, inclusive start.
    return [(start + round(i*1e9/120)/1e9, interpolate(series, start+round(i*1e9/120)/1e9))
            for i in range(math.ceil((end-start)*120)) if start+round(i*1e9/120)/1e9 < end]


def release_metrics(series, target):
    grid = derived_grid(series)
    actual = [v for _, v in grid]
    expected = [interpolate(target, t) for t, _ in grid]
    def smooth(values):
        return [sum(values[max(0,i-3):i+4])/len(values[max(0,i-3):i+4]) for i in range(len(values))]
    actual, expected = smooth(actual), smooth(expected)
    rates = [abs((b-a)-(d-c))*120 for a,b,c,d in zip(actual, actual[1:], expected, expected[1:])]
    def crossing(values, threshold):
        return next((i/120 for i,v in enumerate(values) if v <= threshold), len(values)/120)
    timing = (abs(crossing(actual, expected[0]-.05)-crossing(expected, expected[0]-.05))
              + abs(crossing(actual,.02)-crossing(expected,.02)))/2
    rises, trough, peak, rising = [], actual[0], actual[0], False
    for (t, _), value in zip(grid, actual):
        if not rising:
            trough = min(trough, value)
            if value-trough >= .03:
                rises.append({'time': t, 'kind': 'reapplication'})
                rising, peak = True, value
        else:
            peak = max(peak, value)
            if peak-value >= .03:
                rising, trough = False, value
    return {'rate_error': sum(rates)/len(rates) if rates else 0., 'timing': timing,
            'reapplications': len(rises), 'events': rises}


def simulate_abs(series, limit, enabled=False):
    grid = derived_grid(series)
    locks, rows = [], []
    locked = False
    recovery_since = None
    lock_start = None
    useful = 0.
    end = series[-1][0]
    for t, value in grid:
        threshold = interpolate(limit, t)
        dt = min(1/120, end-t)
        if not enabled:
            if not locked and value > threshold + 1e-10:
                locked, lock_start = True, t
            if locked:
                if value <= threshold-.03 + 1e-10:
                    if recovery_since is None:
                        recovery_since = t
                    if t-recovery_since >= .1-1e-8:
                        locks.append({'start': lock_start, 'end': t, 'recovered': True})
                        locked, recovery_since = False, None
                else:
                    recovery_since = None
        if not locked and threshold-.05-1e-10 <= value <= threshold+1e-10:
            useful += dt
        # Deterministic virtual modulation, not a modified pedal reading.
        effective = min(value, threshold*(.94 if int(round(t*120)) % 12 < 3 else 1.)) if enabled else (value*.25 if locked else value)
        rows.append({'time': t, 'input': value, 'effective': effective, 'limit': threshold, 'locked': locked})
    if locked:
        locks.append({'start': lock_start, 'end': end, 'recovered': False})
    return {'model': MODEL, 'rows': rows, 'locks': locks,
            'locked_seconds': sum(e['end']-e['start'] for e in locks), 'useful_seconds': useful,
            'recovery_seconds': [e['end']-e['start'] if e['recovered'] else None for e in locks]}


def score(exercise, samples, *, surface='Seca', abs_enabled=False):
    if exercise.formula != FORMULA['version']:
        raise ValueError('Versão da fórmula indisponível')
    acquisition = summarize_acquisition([s.elapsed_ns for s in samples], round(exercise.duration*1e9))
    base = {'formula': FORMULA, 'acquisition': asdict(acquisition), 'score': None,
            'components': [], 'events': [], 'simulation': None}
    if acquisition.issues:
        return dict(base, valid=False, feedback='Captura incompleta. Repita: houve lacuna ou frequência insuficiente.')
    if any(not all(math.isfinite(v) for v in asdict(s.controls).values()) for s in samples):
        raise ValueError('Amostras não finitas')
    phases, releases, estimates = [], [], []
    try:
        for a,b in exercise.windows:
            series, estimated = window_series(samples, a,b)
            phases.append(phase_metrics(series, exercise.target, exercise.tolerance))
            releases.append(release_metrics(series, exercise.target))
            estimates.append(estimated)
    except ValueError as error:
        return dict(base, valid=False, feedback=str(error))
    def avg(key): return sum(p[key] for p in phases)/len(phases)
    def rel(key): return sum(p[key] for p in releases)/len(releases)
    release_feedback = 'Ajuste o momento e a velocidade da liberação para acompanhar o alvo.'
    if exercise.family == 'hold':
        specs = [('Tempo na faixa', 1-avg('in_band'), 'Sustente o pedal dentro da faixa indicada.'),
                 ('Precisão', avg('mae')/.3, 'Aproxime a entrada do centro do alvo.'),
                 ('Estabilidade', avg('stability')/.15, 'Reduza as oscilações enquanto sustenta o pedal.'),
                 ('Aquisição', avg('acquisition')/1.5, 'Encontre o alvo e permaneça nele por pelo menos 0,2 s.')]
    elif exercise.family == 'steps':
        specs = [('Precisão das fases', avg('mae')/.3, 'Aproxime cada patamar do alvo.'),
                 ('Transição', avg('acquisition')/1.5, 'Encontre o novo patamar mais cedo e sustente.'),
                 ('Excesso', avg('overshoot')/.3, 'Reduza o excesso ao chegar no patamar.'),
                 ('Estabilidade', avg('stability')/.15, 'Estabilize o pedal após a mudança.')]
    elif exercise.family == 'curve':
        a,b=exercise.windows[0]
        steer,_=window_series(samples,a,b,'steering')
        accel,_=window_series(samples,a,b,'accelerator')
        specs = [('Perfil de freio',avg('mae')/.3,release_feedback),
                 ('Esterço',phase_metrics(steer,exercise.steering,.1)['mae']/.3,'Combine a entrada de volante com turn-in e ápice.'),
                 ('Suavidade',rel('rate_error')/2,release_feedback),
                 ('Aceleração',phase_metrics(accel,exercise.accelerator,.1)['mae']/.3,'Retome o acelerador a partir do marcador de aceleração.')]
    elif exercise.family == 'limit':
        a,b=exercise.windows[0]
        series,_=window_series(samples,a,b)
        sim=simulate_abs(series,SURFACES[surface],abs_enabled)
        base['simulation']=sim
        recovery = max((e['end']-e['start'] if e['recovered'] else 1.5 for e in sim['locks']), default=0.)
        if abs_enabled:
            intensity=phase_metrics(series,((0.,1.),(10.,1.)),.1)
            useful_penalty=1-intensity['in_band']
        else:
            useful_penalty=1-sim['useful_seconds']/(b-a)
        specs=[('Entrada intensa' if abs_enabled else 'Tempo próximo ao limite',useful_penalty,'Com ABS, sustente uma entrada intensa.' if abs_enabled else 'Aproxime-se do limite didático sem ultrapassá-lo.'),
               ('Travamento',sim['locked_seconds']/(b-a),'Alivie o suficiente para recuperar a roda e reaplique próximo ao limite.'),
               ('Recuperação',recovery/1.5,'Recupere a roda aliviando o pedal abaixo do limite.'),
               ('Controle',avg('stability')/.15,'Evite oscilações repetidas; controle a posição do pedal.')]
    elif exercise.family == 'release':
        specs=[('Forma da curva',avg('mae')/.3,release_feedback),('Sincronização',rel('timing')/1.5,release_feedback),
               ('Suavidade',rel('rate_error')/2,release_feedback),('Reaplicações',rel('reapplications')/3,'Continue aliviando sem voltar a aplicar o freio.')]
    else:
        specs=[('Forma da curva',avg('mae')/.3,'Aproxime sua execução da curva personalizada.'),
               ('Tempo na faixa',1-avg('in_band'),'Permaneça dentro da tolerância definida para sua curva.'),
               ('Sincronização',rel('timing')/1.5,'Acompanhe as mudanças da curva no momento indicado.'),
               ('Controle',rel('rate_error')/2,'Faça as transições com a mesma velocidade da curva criada.')]
    components=[{'name':name,'penalty':max(0.,min(1.,penalty)), 'weight':weight, 'feedback':feedback}
                for (name,penalty,feedback),weight in zip(specs,FORMULA['weights'][exercise.family])]
    for c in components: c['score']=100*(1-c['penalty'])
    worst=max(components,key=lambda c:c['penalty'])
    return dict(base,valid=True,score=sum(c['score']*c['weight'] for c in components)/100,
                components=components, phases=phases, release_metrics=releases, estimated_edge_seconds=estimates,
                events=[e for r in releases for e in r['events']],
                feedback=worst['feedback'] if worst['penalty']>1e-8 else 'Alvo acompanhado com controle. Repita para consolidar.')
