from collections import OrderedDict


class Recent:
    def __init__(self, size: int):
        self.size = size
        self._data: OrderedDict = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value) -> None:
        if self.size <= 0:
            return
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.size:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()
