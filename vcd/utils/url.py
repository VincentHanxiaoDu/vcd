import urllib
from vcd.utils.cache import Cacheable


class URL(Cacheable):
    def __init__(self, url, allow_cache=True, rollback_on_fail=True) -> None:
        self._url = url
        super().__init__(allow_cache=allow_cache, rollback_on_fail=rollback_on_fail)

    @property
    def url(self):
        return self._url

    @property
    @Cacheable.cache
    def parsed_url(self):
        return urllib.parse.urlparse(self._url)

    @property
    @Cacheable.cache
    def query_dict(self):
        return urllib.parse.parse_qs(self.parsed_url.query)

    @property
    @Cacheable.cache
    def url(self):
        return urllib.parse.urlunparse(self.parsed_url)

    def with_query_updated(self, query_dict) -> "URL":
        new_query = urllib.parse.urlencode(query_dict, doseq=True)
        replaced_url = self.parsed_url._replace(query=new_query)
        return URL(urllib.parse.urlunparse(replaced_url))
