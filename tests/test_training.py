import numpy as np
import pandas as pd
import pytest
from smartflow.config import EnvConfig
from smartflow.training import train
from smartflow.q_learning_agent import QLearningAgent


def test_training_reproducible_outputs(tmp_path):
    outputs = []
    for name in ('a', 'b'):
        out = tmp_path / name
        agent, data = train(3, 21, env_config=EnvConfig(duration=30), output_dir=out,
                            model_path=out / 'model.npz')
        assert agent.trained and agent.updates == 90
        assert len(data) == 3 and (data.time == 30).all()
        pd.testing.assert_frame_equal(data, pd.read_csv(out / 'training_history.csv'), check_dtype=False)
        np.testing.assert_array_equal(agent.q_table, QLearningAgent.load(out / 'model.npz').q_table)
        outputs.append((agent, data))
    np.testing.assert_array_equal(outputs[0][0].q_table, outputs[1][0].q_table)
    pd.testing.assert_frame_equal(outputs[0][1], outputs[1][1])


def test_interrupted_checkpoint(tmp_path):
    def stop(row, agent):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        train(3, env_config=EnvConfig(duration=20), output_dir=tmp_path,
              model_path=tmp_path / 'model.npz', callback=stop)
    assert len(pd.read_csv(tmp_path / 'training_history.csv')) == 1
    assert QLearningAgent.load(tmp_path / 'model.npz').trained
