"""Masked tabular Q-learning; evaluation never mutates the table or RNG."""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
from zipfile import BadZipFile
import numpy as np
from .config import EnvConfig


@dataclass(frozen=True)
class AgentConfig:
    alpha: float = .1
    gamma: float = .95
    epsilon: float = 1.
    epsilon_min: float = .05
    epsilon_decay: float = .995

    def __post_init__(self):
        if not (0 < self.alpha <= 1 and 0 <= self.gamma <= 1 and
                0 <= self.epsilon_min <= self.epsilon <= 1 and 0 < self.epsilon_decay <= 1):
            raise ValueError('Invalid learning hyperparameters')


class QLearningAgent:
    def __init__(self, env_config=None, config=None, seed=42):
        self.env_config = env_config or EnvConfig()
        self.config = config or AgentConfig()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.epsilon = self.config.epsilon
        self.q_table = np.zeros((int(np.prod(self.env_config.state_shape)), 2))
        self.visits = np.zeros(len(self.q_table), dtype=np.int64)
        self.updates = 0
        self.metadata = {}

    def encode_state(self, state):
        if len(state) != len(self.env_config.state_shape) or any(
                not isinstance(x, (int, np.integer)) for x in state):
            raise ValueError('State must contain seven integer coordinates')
        return int(np.ravel_multi_index(tuple(state), self.env_config.state_shape))

    @staticmethod
    def _actions(actions):
        actions = tuple(actions)
        if not actions or len(set(actions)) != len(actions) or any(a not in (0, 1) for a in actions):
            raise ValueError('Supply a nonempty unique subset of actions 0 and 1')
        return np.array(actions, dtype=int)

    def select_action(self, state, valid_actions, *, evaluate=False):
        actions = self._actions(valid_actions)
        values = self.q_table[self.encode_state(state), actions]
        if not evaluate and self.rng.random() < self.epsilon:
            return int(self.rng.choice(actions))
        best = actions[values == values.max()]
        # Stable tie-breaking makes repeated evaluation fully deterministic.
        return int(best[0] if evaluate else self.rng.choice(best))

    def update(self, state, action, reward, next_state, next_valid_actions,
               *, terminated=False, truncated=False):
        """Bootstrap at time limits: the task is continuing, sampled in short windows.

        True terminal transitions have target=reward. The episode loop stops on
        either flag, but a time-limit truncation retains its next-state value.
        """
        index = self.encode_state(state)
        if action not in (0, 1) or not np.isfinite(reward):
            raise ValueError('Invalid action or reward')
        target = float(reward)
        if not terminated:
            actions = self._actions(next_valid_actions)
            target += self.config.gamma * self.q_table[self.encode_state(next_state), actions].max()
        self.q_table[index, action] += self.config.alpha * (target - self.q_table[index, action])
        self.visits[index] += 1
        self.updates += 1

    def decay_epsilon(self):
        self.epsilon = max(self.config.epsilon_min, self.epsilon * self.config.epsilon_decay)

    @property
    def trained(self):
        return self.updates > 0 and bool(np.any(self.q_table != 0))

    def save(self, path='models/q_table.npz', metadata=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = dict(version=1, env_config=asdict(self.env_config), agent_config=asdict(self.config),
                    epsilon=self.epsilon, seed=self.seed, updates=self.updates,
                    experiment=self.metadata if metadata is None else metadata)
        # Write complete files before replacing previous checkpoints.
        temporary = path.with_suffix('.tmp.npz')
        np.savez_compressed(temporary, q_table=self.q_table, visits=self.visits,
                            metadata=np.array(json.dumps(meta)))
        temporary.replace(path)
        path.with_suffix('.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path='models/q_table.npz'):
        try:
            with np.load(path, allow_pickle=False) as data:
                meta = json.loads(str(data['metadata']))
                if meta['version'] != 1:
                    raise ValueError('Unsupported model version')
                agent = cls(EnvConfig(**meta['env_config']), AgentConfig(**meta['agent_config']), meta['seed'])
                q, visits = data['q_table'], data['visits']
                if (q.shape != agent.q_table.shape or visits.shape != agent.visits.shape or
                        not np.isfinite(q).all() or not np.issubdtype(visits.dtype, np.integer) or
                        np.any(visits < 0) or not 0 <= meta['epsilon'] <= 1 or
                        type(meta['updates']) is not int or meta['updates'] < 0):
                    raise ValueError('Invalid model arrays or metadata')
                agent.q_table[:] = q
                agent.visits[:] = visits
                agent.epsilon, agent.updates = meta['epsilon'], meta['updates']
                agent.metadata = meta['experiment']
                return agent
        except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile) as exc:
            raise ValueError(f'Cannot load model: {exc}') from exc
