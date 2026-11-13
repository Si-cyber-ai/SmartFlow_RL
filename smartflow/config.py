from dataclasses import dataclass

DIRECTIONS = ('N', 'S', 'E', 'W')
SCENARIOS = {
    'Balanced': (.25, .25, .25, .25),
    'NS Rush': (.48, .48, .12, .12),
    'EW Rush': (.12, .12, .48, .48),
    'Uneven': (.60, .16, .10, .22),
    'Dynamic': (.48, .48, .12, .12),
    'Heavy': (.65, .65, .65, .65),
}


@dataclass(frozen=True)
class EnvConfig:
    duration: int = 300
    min_green: int = 5
    max_green: int = 30
    yellow: int = 2
    all_red: int = 1
    service_rate: int = 1
    queue_weight: float = .1
    switch_weight: float = .5

    def __post_init__(self):
        for key in ('duration', 'min_green', 'max_green', 'yellow', 'all_red', 'service_rate'):
            if type(getattr(self, key)) is not int or getattr(self, key) < 1:
                raise ValueError(f'{key} must be a positive integer')
        if self.max_green < self.min_green:
            raise ValueError('max_green must be >= min_green')
        if not (0 <= self.queue_weight < float('inf') and 0 <= self.switch_weight < float('inf')):
            raise ValueError('Reward weights must be finite and nonnegative')

    @property
    def state_shape(self):
        # Exact green clock and exact transition clock; four coarse queue buckets.
        return (3, 3, 3, 3, 2, self.max_green + 1, 1 + self.yellow + self.all_red)
