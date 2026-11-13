"""One step = one second. Arrivals precede service; new arrivals can leave immediately.

State: four queue buckets, active (old during transition) phase, exact green
elapsed time, transition countdown. Countdown > all_red means yellow.
The horizon is a truncation, never a physical terminal event.
"""
from collections import deque
from dataclasses import dataclass
import numpy as np
from .config import DIRECTIONS, SCENARIOS, EnvConfig


@dataclass
class Vehicle:
    id: int
    arrival: int
    direction: str
    departure: int | None = None
    waiting: int = 0


def arrival_trace(config, scenario, seed):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown traffic scenario')
    rates = np.tile(SCENARIOS[scenario], (config.duration, 1))
    if scenario == 'Dynamic':
        rates[config.duration // 2:] = SCENARIOS['EW Rush']
    return np.random.default_rng(seed).poisson(rates)


class TrafficEnv:
    def __init__(self, config=None, scenario='Balanced', seed=42, trace=None):
        self.config = config or EnvConfig()
        self.scenario = scenario
        self.external_trace = None if trace is None else np.array(trace, copy=True)
        self.reset(seed)

    def reset(self, seed=None, scenario=None):
        if scenario is not None:
            self.scenario = scenario
        if self.scenario not in SCENARIOS:
            raise ValueError('Unknown traffic scenario')
        self.trace = (arrival_trace(self.config, self.scenario, seed) if self.external_trace is None
                      else self.external_trace.copy())
        if (self.trace.shape != (self.config.duration, 4) or
                not np.issubdtype(self.trace.dtype, np.integer) or np.any(self.trace < 0)):
            raise ValueError('Arrival trace must be nonnegative integer counts [duration, 4]')
        self.queues = {d: deque() for d in DIRECTIONS}
        self.vehicles = []
        self.time = self.phase = self.elapsed = self.remaining = 0
        self.queue_sum = self.max_queue = self.switches = self.served = self.wait_sum = 0
        self.total_reward = 0.
        self.last_departures = []
        return self.get_state()

    def get_state(self):
        buckets = tuple(min(len(self.queues[d]) // 4, 2) for d in DIRECTIONS)
        return (*buckets, self.phase, self.elapsed, self.remaining)

    def get_valid_actions(self):
        if self.remaining or self.elapsed < self.config.min_green:
            return (0,)
        if self.elapsed >= self.config.max_green:
            return (1,)
        return (0, 1)

    def step(self, action):
        if self.time >= self.config.duration:
            raise RuntimeError('Episode complete; call reset')
        if action not in (0, 1):
            raise ValueError('Action must be 0 or 1')
        valid = self.get_valid_actions()
        applied = action if action in valid else valid[0]
        switched = applied == 1
        if switched:
            self.remaining = self.config.yellow + self.config.all_red
            self.switches += 1
        service_phase = self.phase if self.remaining == 0 else None
        self.last_departures = []
        for i, d in enumerate(DIRECTIONS):
            for _ in range(int(self.trace[self.time, i])):
                v = Vehicle(len(self.vehicles), self.time, d)
                self.vehicles.append(v)
                self.queues[d].append(v)
            if service_phase == i // 2:
                for _ in range(min(len(self.queues[d]), self.config.service_rate)):
                    v = self.queues[d].popleft()
                    v.departure = self.time
                    v.waiting = self.time - v.arrival
                    self.served += 1
                    self.wait_sum += v.waiting
                    self.last_departures.append(v)
        count = sum(map(len, self.queues.values()))
        self.queue_sum += count
        self.max_queue = max(self.max_queue, count)
        reward = -self.config.queue_weight * count - self.config.switch_weight * switched
        self.total_reward += reward
        self.time += 1
        if self.remaining:
            self.remaining -= 1
            if self.remaining == 0:
                self.phase = 1 - self.phase
                self.elapsed = 0
        else:
            self.elapsed += 1
        return self.get_state(), reward, False, self.time >= self.config.duration, {
            'switch_initiated': switched, 'applied_action': applied,
            'service_phase': service_phase, 'arrivals': self.trace[self.time - 1].copy(),
        }

    def get_metrics(self):
        return dict(time=self.time, arrived=len(self.vehicles), served=self.served,
                    remaining=sum(map(len, self.queues.values())),
                    avg_wait=self.wait_sum / self.served if self.served else 0.,
                    avg_queue=self.queue_sum / self.time if self.time else 0.,
                    max_queue=self.max_queue, reward=self.total_reward, switches=self.switches,
                    unresolved_delay=sum(self.time - v.arrival for q in self.queues.values() for v in q))

    def get_render_data(self):
        status = ('green' if not self.remaining else
                  'yellow' if self.remaining > self.config.all_red else 'all-red')
        signals = {d: ('green' if i // 2 == self.phase and status == 'green' else
                       'yellow' if i // 2 == self.phase and status == 'yellow' else 'red')
                   for i, d in enumerate(DIRECTIONS)}
        return dict(queues={d: [v.id for v in q] for d, q in self.queues.items()},
                    signals=signals, phase=self.phase, target=1-self.phase if self.remaining else self.phase,
                    status=status, remaining=self.remaining, elapsed=self.elapsed,
                    departures=[vars(v).copy() for v in self.last_departures], time=self.time)
