import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
import pytest
from smartflow.config import EnvConfig
from smartflow.environment import TrafficEnv
from smartflow.live_simulation import LiveSimulation, policy_snapshot, scenario_rates
from smartflow.paths import MODEL
from smartflow.q_learning_agent import QLearningAgent
from smartflow.visualization import intersection_svg


def test_decision_values_and_factual_explanations():
    agent = QLearningAgent.load(MODEL)
    env = TrafficEnv(agent.env_config)
    original = agent.q_table.copy()
    first = policy_snapshot(env, 'Trained Q-Learning', agent)
    assert first['valid'] == (0,) and 'only legal' in first['explanation']
    for _ in range(env.config.min_green):
        env.step(0)
    index = agent.encode_state(env.get_state())
    agent.q_table[index] = [2., 4.]
    row = policy_snapshot(env, 'Trained Q-Learning', agent)
    assert row['action'] == 1 and row['q_values'] == {0: 2., 1: 4.}
    assert 'higher Q-value' in row['explanation']
    agent.q_table[index] = [3., 3.]
    assert 'tied' in policy_snapshot(env, 'Trained Q-Learning', agent)['explanation']
    agent.q_table[:] = original  # The saved model file is never written.


def test_shared_trace_playback_history_and_no_learning():
    agent = QLearningAgent.load(MODEL)
    q, visits = agent.q_table.copy(), agent.visits.copy()
    rng, epsilon, updates = repr(agent.rng.bit_generator.state), agent.epsilon, agent.updates
    live = LiveSimulation(EnvConfig(duration=60), 'NS Rush', 456, agent=agent, paired=True, history_limit=12)
    np.testing.assert_array_equal(live.envs['Fixed-Time'].trace, live.envs['Trained Q-Learning'].trace)
    live.start()
    live.step()
    live.pause()
    assert live.status == 'paused' and live.env.time == 1
    live.resume()
    assert live.status == 'running'
    for _ in range(59):
        live.step()
    assert live.status == 'complete' and not live.step()
    assert {env.time for env in live.envs.values()} == {60}
    assert len(live.histories['Fixed-Time']) == 12
    for name, env in live.envs.items():
        assert env.get_metrics()['arrived'] == int(live.trace.sum())
        assert live.histories[name][-1]['North'] == len(env.queues['N'])
        last = live.decisions[name]
        assert last['time'] == 59
        assert last['applied_action'] == last['action']
        assert last['reward'] == pytest.approx(-.1*env.get_metrics()['remaining'] - .5*int(last['action'] == 1))
    np.testing.assert_array_equal(agent.q_table, q)
    np.testing.assert_array_equal(agent.visits, visits)
    assert (repr(agent.rng.bit_generator.state), agent.epsilon, agent.updates) == (rng, epsilon, updates)
    trace = live.trace.copy()
    live.reset()
    assert live.status == 'idle' and live.env.time == 0 and not live.decisions
    np.testing.assert_array_equal(live.env.trace, trace)
    assert len(live.histories['Fixed-Time']) == 1


def test_svg_animated_ids_and_signals_are_real():
    live = LiveSimulation(EnvConfig(duration=40), 'Balanced', 3)
    ns = {'s': 'http://www.w3.org/2000/svg'}
    for _ in range(35):
        live.step()
        data = live.env.get_render_data()
        svg = ET.fromstring(intersection_svg(data, live.previous['Fixed-Time'], True))
        queued = svg.findall('.//s:g[@class="queued-vehicle"]', ns)
        departed = svg.findall('.//s:g[@class="departed-vehicle"]', ns)
        assert {int(g.attrib['data-vehicle-id']) for g in queued} == {v for ids in data['queues'].values() for v in ids}
        assert {int(g.attrib['data-vehicle-id']) for g in departed} == {v['id'] for v in data['departures']}
        assert len(queued) == live.env.get_metrics()['remaining']
        static = intersection_svg(data)
        assert 'animateTransform' not in static and 'departed-vehicle' not in static
        for direction, signal in data['signals'].items():
            assert f'aria-label="{direction} signal {signal}"' in static


def test_scenarios_and_missing_model():
    assert scenario_rates('Dynamic', 149, 300)['N'] == .48
    assert scenario_rates('Dynamic', 150, 300)['N'] == .12
    assert sum(scenario_rates('Heavy', 0, 300).values()) > 2
    with pytest.raises(ValueError, match='Load or train'):
        LiveSimulation(EnvConfig(), 'Balanced', 1, paired=True)


def test_protected_sources_and_experiments_unchanged():
    root = Path(__file__).resolve().parents[1]
    baseline = json.loads((root / 'docs/dashboard_preservation_hashes.json').read_text())
    for relative, expected in baseline.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
