import argparse
from smartflow.config import SCENARIOS
from smartflow.paths import MODEL, RESULTS
from smartflow.q_learning_agent import QLearningAgent
from smartflow.evaluation import compare
from smartflow.charts import generate_charts


def main():
    p = argparse.ArgumentParser(description='Evaluate on matched unseen arrival traces')
    p.add_argument('--episodes', type=int, default=20)
    p.add_argument('--seed', type=int, default=100000)
    p.add_argument('--scenario', choices=list(SCENARIOS))
    p.add_argument('--duration', type=int)
    p.add_argument('--green-duration', type=int, default=15)
    p.add_argument('--model', default=str(MODEL))
    p.add_argument('--output-dir', default=str(RESULTS))
    args = p.parse_args()
    _, _, paired = compare(QLearningAgent.load(args.model), args.episodes, args.seed,
                            [args.scenario] if args.scenario else None, args.duration,
                            args.green_duration, args.output_dir)
    print(paired.to_string(index=False))
    from pathlib import Path
    if (Path(args.output_dir) / 'training_history.csv').exists():
        generate_charts(args.output_dir)


if __name__ == '__main__':
    main()
