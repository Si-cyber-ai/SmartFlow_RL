import argparse
from smartflow.config import EnvConfig, SCENARIOS
from smartflow.paths import MODEL, RESULTS
from smartflow.q_learning_agent import AgentConfig
from smartflow.training import train


def main():
    p = argparse.ArgumentParser(description='Train SmartFlow tabular Q-Learning')
    p.add_argument('--episodes', type=int, default=1000)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--scenario', choices=[*SCENARIOS, 'Mixed'], default='NS Rush')
    p.add_argument('--duration', type=int, default=300)
    p.add_argument('--alpha', type=float, default=.1)
    p.add_argument('--gamma', type=float, default=.95)
    p.add_argument('--epsilon', type=float, default=1.)
    p.add_argument('--epsilon-min', type=float, default=.05)
    p.add_argument('--epsilon-decay', type=float, default=.995)
    p.add_argument('--output-dir', default=str(RESULTS))
    p.add_argument('--model', default=str(MODEL))
    args = p.parse_args()
    agent, history = train(args.episodes, args.seed, args.scenario, EnvConfig(duration=args.duration),
                           AgentConfig(args.alpha, args.gamma, args.epsilon, args.epsilon_min, args.epsilon_decay),
                           args.output_dir, args.model,
                           lambda row, a: print(f"Episode {row['episode']}: reward={row['reward']:.1f}, epsilon={a.epsilon:.3f}")
                           if row['episode'] % 100 == 0 else None)
    print(f'Completed {len(history)} episodes; {agent.updates} updates; {(agent.q_table != 0).sum()} nonzero Q entries')


if __name__ == '__main__':
    main()
