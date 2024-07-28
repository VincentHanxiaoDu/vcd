import time


def timer(timeout):
    start = time.time()

    def is_timeout():
        return time.time() - start > timeout

    return is_timeout
