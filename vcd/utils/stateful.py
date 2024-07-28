class Stateful:
    def __init__(self) -> None:
        self._val = None

    def get(self, block=False, is_timeout=None):
        if block:
            while self._val is None:
                if is_timeout is not None and is_timeout():
                    raise TimeoutError()
                pass
        return self._val

    def set(self, new_value):
        self._val = new_value
