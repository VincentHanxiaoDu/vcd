import queue
class WriteableQueue(queue.Queue):

    def write(self, data):
        if data:
            self.put(data)

    def __iter__(self):
        return iter(self.get, None)

    def close(self):
        self.put(None)
