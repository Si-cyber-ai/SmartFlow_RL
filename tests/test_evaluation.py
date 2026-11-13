import numpy as np
import pandas as pd
import pytest
from smartflow.config import EnvConfig
from smartflow.controllers import FixedTimeController
from smartflow.environment import TrafficEnv
from smartflow.training import train
from smartflow.evaluation import compare, improvement


def test_fair_evaluation_and_no_mutation(tmp_path):
    agent, history = train(2, env_config=EnvConfig(duration=30), output_dir=tmp_path,
                           model_path=tmp_path / 'model.npz')
    q, visits, epsilon, updates = agent.q_table.copy(), agent.visits.copy(), agent.epsilon, agent.updates
    history_bytes = (tmp_path / 'training_history.csv').read_bytes()
    data, summary, pairs = compare(agent, 2, scenarios=['NS Rush', 'Balanced'], output_dir=tmp_path)
    assert len(data) == 8 and len(summary) == 4 and len(pairs) == 14
    assert (data.groupby(['scenario', 'seed']).trace_sha256.nunique() == 1).all()
    assert (data.groupby(['scenario', 'seed']).arrived.nunique() == 1).all()
    assert (data.arrived == data.served + data.remaining).all()
    np.testing.assert_array_equal(q, agent.q_table)
    np.testing.assert_array_equal(visits, agent.visits)
    assert (agent.epsilon, agent.updates) == (epsilon, updates)
    assert (tmp_path / 'training_history.csv').read_bytes() == history_bytes
    repeated, _, _ = compare(agent, 2, scenarios=['NS Rush', 'Balanced'], output_dir=tmp_path)
    pd.testing.assert_frame_equal(data, repeated)
    with pytest.raises(ValueError, match='disjoint'):
        compare(agent, seed=42, output_dir=tmp_path)


def test_metric_math_and_baseline():
    assert improvement(10, 8) == 20
    assert improvement(10, 8, True) == -20
    assert improvement(0, 0) == 0
    assert np.isnan(improvement(0, 1))
    e, controller = TrafficEnv(), FixedTimeController()
    for _ in range(15):
        e.step(controller.action(e))
    assert controller.action(e) == 1
    e.step(1)
    assert controller.action(e) == 0
