"""Dashboard inference and presentation only; no training or disk writes."""
from collections import deque
from .config import DIRECTIONS, SCENARIOS
from .controllers import FixedTimeController
from .environment import TrafficEnv, arrival_trace

SCENARIO_LABELS = {
    'Balanced': 'Balanced Traffic', 'NS Rush': 'North–South Rush Hour',
    'EW Rush': 'East–West Rush Hour', 'Uneven': 'Uneven Traffic',
    'Dynamic': 'Dynamic Traffic', 'Heavy': 'Heavy Congestion',
}
ROAD_NAMES = dict(N='North', S='South', E='East', W='West')
ACTION_NAMES = {0: 'KEEP', 1: 'SWITCH'}


def scenario_rates(scenario, time, duration):
    selected = 'EW Rush' if scenario == 'Dynamic' and time >= duration // 2 else scenario
    return dict(zip(DIRECTIONS, SCENARIOS[selected]))


def policy_snapshot(env, controller, agent=None, fixed_green=15):
    """Inspect an exact decision state without mutating the agent or its RNG."""
    state, valid = env.get_state(), env.get_valid_actions()
    snapshot = dict(time=env.time, state=state, queues={d: len(env.queues[d]) for d in DIRECTIONS},
                    phase=env.phase, elapsed=env.elapsed, remaining=env.remaining,
                    valid=valid, encoded=None, q_values={}, controller=controller)
    if controller == 'Trained Q-Learning':
        if agent is None or not agent.trained:
            raise ValueError('Load or train a model before using Q-Learning.')
        if env.config.state_shape != agent.env_config.state_shape:
            raise ValueError('Live timing configuration is incompatible with the model.')
        index = agent.encode_state(state)
        values = {a: float(agent.q_table[index, a]) for a in valid}
        action = agent.select_action(state, valid, evaluate=True)
        snapshot.update(encoded=index, q_values=values)
        if len(valid) == 1:
            reason = f'{ACTION_NAMES[action]} is the only legal action under the signal timing constraints.'
        elif len(set(values.values())) == 1:
            reason = f'Legal Q-values are tied; deterministic evaluation selects {ACTION_NAMES[action]}.'
        else:
            reason = f'The trained policy selects {ACTION_NAMES[action]} because it has the higher Q-value among legal actions.'
    else:
        action = FixedTimeController(fixed_green).action(env)
        reason = f'Fixed timing selects {ACTION_NAMES[action]} under its {fixed_green}-second green plan and safety constraints.'
    snapshot.update(action=action, explanation=reason)
    return snapshot


class LiveSimulation:
    """Synchronized playback on one saved in-memory exogenous arrival trace."""
    def __init__(self, config, scenario, seed, controller='Fixed-Time', agent=None,
                 fixed_green=15, paired=False, history_limit=240):
        self.config, self.scenario, self.seed = config, scenario, seed
        self.controller, self.agent, self.fixed_green = controller, agent, fixed_green
        self.paired = paired
        self.trace = arrival_trace(config, scenario, seed)
        self.controllers = ('Fixed-Time', 'Trained Q-Learning') if paired else (controller,)
        if 'Trained Q-Learning' in self.controllers and (agent is None or not agent.trained):
            raise ValueError('Load or train a model before using Q-Learning.')
        self.envs = {name: TrafficEnv(config, scenario, trace=self.trace) for name in self.controllers}
        self.histories = {name: deque(maxlen=history_limit) for name in self.controllers}
        self.previous, self.decisions = {}, {}
        self.status = 'idle'
        self._record()

    @property
    def env(self):
        return self.envs[self.controller]

    def _record(self):
        for name, env in self.envs.items():
            self.histories[name].append(dict(time=env.time, **{ROAD_NAMES[d]: len(env.queues[d]) for d in DIRECTIONS}))

    def reset(self):
        for env in self.envs.values():
            env.reset()  # Reuses the original external trace.
        for history in self.histories.values():
            history.clear()
        self.previous.clear()
        self.decisions.clear()
        self.status = 'idle'
        self._record()

    def start(self):
        if self.status == 'complete':
            self.reset()
        if self.status == 'idle':
            self.status = 'running'

    def pause(self):
        if self.status == 'running':
            self.status = 'paused'

    def resume(self):
        if self.status == 'paused':
            self.status = 'running'

    def step(self):
        if self.status == 'complete':
            return False
        for name, env in self.envs.items():
            self.previous[name] = env.get_render_data()
            snapshot = policy_snapshot(env, name, self.agent, self.fixed_green)
            _, reward, _, _, info = env.step(snapshot['action'])
            snapshot.update(reward=reward, applied_action=info['applied_action'], service_phase=info['service_phase'])
            self.decisions[name] = snapshot
        self._record()
        self.status = 'complete' if self.env.time >= self.config.duration else ('running' if self.status == 'running' else 'paused')
        return True
