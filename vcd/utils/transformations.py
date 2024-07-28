def get_index(l, item):
    try:
        return l.index(item)
    except ValueError:
        return None


def nvl(x, default):
    return x if x is not None else default