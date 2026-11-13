class FixedTimeController:
    def __init__(self, green_duration=15):
        if type(green_duration) is not int or green_duration < 1:
            raise ValueError('Green duration must be a positive integer')
        self.green_duration = green_duration

    def action(self, env):
        requested = int(env.elapsed >= self.green_duration and not env.remaining)
        valid = env.get_valid_actions()
        return requested if requested in valid else valid[0]
