import numpy as np
import pytest
from smartflow.config import EnvConfig, SCENARIOS
from smartflow.environment import TrafficEnv


def test_initial_reset_and_seed():
    a = TrafficEnv(seed=7)
    assert a.get_state() == (0, 0, 0, 0, 0, 0, 0)
    trace = a.trace.copy()
    for _ in range(10):
        a.step(0)
    a.reset(7)
    assert np.array_equal(trace, a.trace)
    assert a.get_metrics()['arrived'] == 0


def test_fifo_reward_and_wait():
    trace = np.zeros((10, 4), dtype=int)
    trace[0] = (2, 0, 1, 0)
    e = TrafficEnv(EnvConfig(duration=10), trace=trace)
    _, reward, _, _, _ = e.step(0)
    assert reward == pytest.approx(-.2)
    assert e.get_metrics()['remaining'] == 2
    assert e.vehicles[0].departure == 0
    e.step(0)
    assert e.vehicles[1].departure == 1
    assert e.get_metrics()['avg_wait'] == .5
    assert e.vehicles[2].departure is None


def test_timing_and_transition():
    e = TrafficEnv(EnvConfig(duration=50), trace=np.ones((50, 4), dtype=int))
    for _ in range(5):
        assert e.get_valid_actions() == (0,)
        assert not e.step(1)[4]['switch_initiated']
    assert e.get_valid_actions() == (0, 1)
    for action in (1, 1, 1):
        assert e.step(action)[4]['service_phase'] is None
    assert e.phase == 1 and e.elapsed == 0
    assert e.step(0)[4]['service_phase'] == 1


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_safety_conservation_and_horizon(scenario):
    e = TrafficEnv(scenario=scenario)
    for _ in range(300):
        before = e.get_render_data()
        assert sum(s == 'green' for s in before['signals'].values()) <= 2
        state, reward, terminal, truncated, info = e.step(0)
        assert e.elapsed <= e.config.max_green
        assert e.get_metrics()['arrived'] == e.served + e.get_metrics()['remaining']
        for v in e.last_departures:
            assert ('NSEW'.index(v.direction) // 2) == info['service_phase']
        assert not terminal
    assert truncated and e.switches > 0
    with pytest.raises(RuntimeError):
        e.step(0)


def test_invalid_config_trace_and_action():
    with pytest.raises(ValueError):
        EnvConfig(min_green=40)
    with pytest.raises(ValueError):
        TrafficEnv(trace=np.zeros((3, 4)))
    with pytest.raises(ValueError):
        TrafficEnv().step(2)
