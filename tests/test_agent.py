import numpy as np
import pytest
from smartflow.config import EnvConfig
from smartflow.environment import TrafficEnv
from smartflow.q_learning_agent import AgentConfig, QLearningAgent


def test_initialization_encoding_validation():
    a = QLearningAgent()
    assert a.q_table.shape == (20088, 2)
    assert not a.q_table.any() and not a.trained
    assert a.encode_state((0, 0, 0, 0, 0, 0, 0)) == 0
    with pytest.raises(ValueError):
        a.encode_state((9, 0, 0, 0, 0, 0, 0))
    with pytest.raises(ValueError):
        AgentConfig(alpha=0)


def test_exploration_greedy_and_mask():
    a = QLearningAgent()
    s = (0,) * 7
    assert {a.select_action(s, (0, 1)) for _ in range(100)} == {0, 1}
    a.q_table[0] = [1, 100]
    for _ in range(20):
        assert a.select_action(s, (0,), evaluate=True) == 0
        assert a.select_action(s, (0, 1), evaluate=True) == 1
    with pytest.raises(ValueError):
        a.select_action(s, ())


def test_bellman_terminal_truncation_and_decay():
    a = QLearningAgent(config=AgentConfig(alpha=.5, gamma=.9))
    s, n = (0,) * 7, (0, 0, 0, 0, 0, 1, 0)
    a.q_table[a.encode_state(n)] = [10, 100]
    a.update(s, 0, 2, n, (0,))
    assert a.q_table[0, 0] == pytest.approx(5.5)
    a.update(s, 1, 2, n, (), terminated=True)
    assert a.q_table[0, 1] == 1
    a.q_table[0, 0] = 0
    a.update(s, 0, 2, n, (0,), truncated=True)
    assert a.q_table[0, 0] == pytest.approx(5.5)
    for _ in range(2000):
        a.decay_epsilon()
    assert a.epsilon == .05


def test_environment_learning_and_persistence(tmp_path):
    e = TrafficEnv(EnvConfig(duration=60))
    a = QLearningAgent(e.config)
    for episode in range(5):
        s = e.reset(episode)
        done = False
        while not done:
            action = a.select_action(s, e.get_valid_actions())
            n, r, term, trunc, info = e.step(action)
            a.update(s, info['applied_action'], r, n, e.get_valid_actions(), terminated=term, truncated=trunc)
            s, done = n, term or trunc
        a.decay_epsilon()
    assert a.trained and a.updates == 300
    path = tmp_path / 'model.npz'
    a.save(path, {'episodes': 5})
    loaded = QLearningAgent.load(path)
    np.testing.assert_array_equal(a.q_table, loaded.q_table)
    assert loaded.metadata['episodes'] == 5
    before = loaded.q_table.copy()
    for _ in range(20):
        loaded.select_action(s, e.get_valid_actions(), evaluate=True)
    np.testing.assert_array_equal(before, loaded.q_table)
    path.write_bytes(b'broken')
    with pytest.raises(ValueError, match='Cannot load'):
        QLearningAgent.load(path)


def test_invalid_metadata_and_training_randomness(tmp_path):
    import json
    a, b = QLearningAgent(seed=9), QLearningAgent(seed=9)
    state = (0,) * 7
    assert [a.select_action(state, (0, 1)) for _ in range(40)] == [b.select_action(state, (0, 1)) for _ in range(40)]
    path = tmp_path / 'invalid.npz'
    a.save(path)
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        table, visits = data['q_table'].copy(), data['visits'].copy()
    metadata['epsilon'] = 2
    np.savez(path, q_table=table, visits=visits, metadata=np.array(json.dumps(metadata)))
    with pytest.raises(ValueError, match='Invalid model'):
        QLearningAgent.load(path)
