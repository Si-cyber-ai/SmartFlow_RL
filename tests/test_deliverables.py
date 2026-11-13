import json
from pathlib import Path
import pandas as pd
from smartflow.q_learning_agent import QLearningAgent


def test_bundled_artifacts():
    root = Path(__file__).resolve().parents[1]
    for name in ('README.md', 'PROGRESS.md', 'requirements.txt', 'app.py', 'train.py', 'evaluate.py',
                 'docs/PROJECT_REPORT.md', 'docs/DEMO_GUIDE.md',
                 'docs/VALIDATION.md', 'docs/SUBMISSION_CHECKLIST.md', 'results/training_charts.png',
                 'results/comparison_charts.png'):
        assert (root / name).stat().st_size > 0, name
    agent = QLearningAgent.load(root / 'models/q_table.npz')
    history = pd.read_csv(root / 'results/training_history.csv')
    evaluations = pd.read_csv(root / 'results/evaluation_results.csv')
    metadata = json.loads((root / 'results/evaluation_metadata.json').read_text())
    assert agent.trained
    assert agent.metadata['episodes_completed'] == len(history)
    assert len(evaluations) == len(metadata['scenarios']) * metadata['episodes_per_scenario'] * 2
    assert set(evaluations.seed).isdisjoint(set(history.seed))
