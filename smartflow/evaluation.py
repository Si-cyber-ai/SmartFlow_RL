"""Paired evaluation on immutable, pre-generated arrivals; no learning calls."""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .config import SCENARIOS
from .controllers import FixedTimeController
from .environment import TrafficEnv, arrival_trace
from .paths import RESULTS

METRICS = ('avg_wait', 'avg_queue', 'max_queue', 'served', 'remaining', 'reward', 'switches')


def improvement(baseline, rl, higher_is_better=False):
    if baseline == 0:
        return 0. if rl == 0 else float('nan')
    return (rl - baseline if higher_is_better else baseline - rl) / abs(baseline) * 100


def compare(agent, episodes=20, seed=100000, scenarios=None, duration=None,
            green_duration=15, output_dir=RESULTS):
    if not agent.trained:
        raise ValueError('Train or load a trained model before evaluation')
    if type(episodes) is not int or episodes < 1:
        raise ValueError('Episodes must be a positive integer')
    scenarios = tuple(SCENARIOS) if scenarios is None else tuple(scenarios)
    if not scenarios or any(s not in SCENARIOS for s in scenarios):
        raise ValueError('Select at least one valid scenario')
    used_seeds = set(agent.metadata.get('training_seeds', []))
    if used_seeds.intersection(range(seed, seed + episodes)):
        raise ValueError('Evaluation seeds must be disjoint from training seeds')
    config = replace(agent.env_config, duration=duration or agent.env_config.duration)
    baseline = FixedTimeController(green_duration)
    rows = []
    for scenario in scenarios:
        for run in range(episodes):
            trace = arrival_trace(config, scenario, seed + run)
            digest = hashlib.sha256(trace.tobytes()).hexdigest()
            for controller in ('Fixed-Time', 'Q-Learning'):
                env = TrafficEnv(config, scenario, trace=trace)
                while True:
                    action = (baseline.action(env) if controller == 'Fixed-Time' else
                              agent.select_action(env.get_state(), env.get_valid_actions(), evaluate=True))
                    _, _, term, trunc, _ = env.step(action)
                    if term or trunc:
                        break
                rows.append(dict(scenario=scenario, seed=seed + run, controller=controller,
                                 trace_sha256=digest, **env.get_metrics()))
    frame = pd.DataFrame(rows)
    summary = frame.groupby(['scenario', 'controller'])[list(METRICS)].agg(['mean', 'std'])
    summary.columns = ['_'.join(c) for c in summary.columns]
    summary = summary.reset_index()
    paired = []
    for scenario in scenarios:
        pairs = frame[frame.scenario == scenario].pivot(index='seed', columns='controller', values=list(METRICS))
        for metric in METRICS:
            base, rl = pairs[metric]['Fixed-Time'], pairs[metric]['Q-Learning']
            differences = rl - base
            paired.append(dict(scenario=scenario, metric=metric, baseline=base.mean(), rl=rl.mean(),
                               improvement_pct=improvement(base.mean(), rl.mean(), metric in ('served', 'reward')),
                               paired_difference_mean=differences.mean(),
                               paired_difference_se=differences.std(ddof=1) / np.sqrt(episodes) if episodes > 1 else 0))
    paired = pd.DataFrame(paired)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out / 'evaluation_results.csv', index=False)
    summary.to_csv(out / 'evaluation_summary.csv', index=False)
    paired.to_csv(out / 'improvements.csv', index=False)
    metadata = dict(episodes_per_scenario=episodes, scenarios=scenarios, first_seed=seed,
                    env_config=asdict(config), fixed_green=green_duration,
                    model_q_sha256=hashlib.sha256(agent.q_table.tobytes()).hexdigest(),
                    training_experiment=agent.metadata, evaluation_epsilon=0)
    (out / 'evaluation_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return frame, summary, paired
