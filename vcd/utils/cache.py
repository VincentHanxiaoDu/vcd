import logging
import copy

logger = logging.getLogger(__name__)


class Cacheable:

    @staticmethod
    def cache(method):
        cache_key = method.__name__

        def method_wrapper(self, *args, **kwargs):
            if not isinstance(self, Cacheable):
                raise TypeError(
                    f"The class {self.__class__.__name__} must inherit from Cachable to use the cache decorator."
                )
            if cache_key in self._cache and self._allow_cache:
                logger.debug(f"Cache hit for {cache_key}")
                return copy.deepcopy(self.get_cache(cache_key))
            self._rollback_flag = False
            res = None
            try:
                res = method(self, *args, **kwargs)
            except Exception as e:
                if self._rollback_on_fail:
                    self.rollback_cache()
                raise e
            if res is None and self._rollback_on_fail:
                self.rollback_cache()
            if self._allow_cache and not self._rollback_flag:
                self.update_cache(cache_key, res)
            return res

        return method_wrapper

    def __init__(self, allow_cache=True, rollback_on_fail=True):
        self._allow_cache = allow_cache
        self._cache = {}
        self._rollback_flag = False
        self._rollback_on_fail = rollback_on_fail

    def get_cache(self, key):
        return self._cache.get(key)

    def update_cache(self, key, value):
        self._cache[key] = value

    def delete_cache(self, key):
        if key in self._cache:
            del self._cache[key]

    def rollback_cache(self):
        self._rollback_flag = True

    def clear_cache(self):
        self._cache = {}
