"""Real episode training with a checkpoint after every completed episode."""
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from .config import EnvConfig, SCENARIOS
from .environment import TrafficEnv
from .paths import MODEL, RESULTS
from .q_learning_agent import QLearningAgent, AgentConfig


def train(episodes=1000, seed=42, scenario='NS Rush', env_config=None,
          agent_config=None, output_dir=RESULTS, model_path=MODEL, callback=None):
    if type(episodes) is not int or episodes < 1:
        raise ValueError('Episodes must be a positive integer')
    if scenario != 'Mixed' and scenario not in SCENARIOS:
        raise ValueError('Unknown traffic scenario')
    config = env_config or EnvConfig()
    agent = QLearningAgent(config, agent_config or AgentConfig(), seed)
    rows = []
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Separate seeds for the controller and traffic; explicit provenance for each row.
    scenarios = tuple(SCENARIOS) if scenario == 'Mixed' else (scenario,)
    agent.metadata = dict(episodes_requested=episodes, training_seed=seed,
                          scenario=scenario, env_config=asdict(config),
                          training_seeds=[seed + i for i in range(episodes)])
    try:
        for episode in range(episodes):
            selected = scenarios[episode % len(scenarios)]
            env = TrafficEnv(config, selected, seed + episode)
            state = env.get_state()
            epsilon = agent.epsilon
            while True:
                action = agent.select_action(state, env.get_valid_actions())
                nxt, reward, terminated, truncated, info = env.step(action)
                agent.update(state, info['applied_action'], reward, nxt, env.get_valid_actions(),
                             terminated=terminated, truncated=truncated)
                state = nxt
                if terminated or truncated:
                    break
            rows.append(dict(episode=episode + 1, **env.get_metrics(), epsilon=epsilon,
                             scenario=selected, seed=seed + episode,
                             visited_states=int((agent.visits > 0).sum())))
            agent.decay_epsilon()
            # CSV append keeps completed episode records if the process is interrupted.
            pd.DataFrame([rows[-1]]).to_csv(out / 'training_history.csv', mode='w' if episode == 0 else 'a',
                                          header=episode == 0, index=False)
            agent.metadata['episodes_completed'] = episode + 1
            if (episode + 1) % 50 == 0 or episode + 1 == episodes:
                agent.save(model_path)
            if callback:
                callback(rows[-1], agent)
    except (KeyboardInterrupt, Exception):
        agent.metadata['interrupted'] = True
        agent.save(model_path)
        raise
    return agent, pd.DataFrame(rows)
