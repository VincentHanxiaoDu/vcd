import requests
import logging

logger = logging.getLogger(__name__)


class RequestFailedException(Exception):
    pass


class UA:
    DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


class HttpClient:
    def __init__(self, headers, proxies, retry: int = 3) -> None:
        self.headers = headers or {}
        self.proxies = proxies or {}
        self.retry = retry

    def _get_updated_headers(self, headers=None):
        headers = headers or {}
        headers.update(self.headers)
        return headers

    def _retry(self, func, *args, **kwargs):
        for i in range(self.retry):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warn(
                    f"Failed to execute {func.__name__}, retrying... {i + 1}/{self.retry}"
                )
        raise RequestFailedException(f"Failed to execute {func.__name__}")

    def _get(self, url, accepted_status={200}, **kwargs):
        res = requests.get(url, proxies=self.proxies, **kwargs)
        if res.status_code not in accepted_status:
            logger.warn(f"Failed to get {url}, status code: {res.status_code}")
            raise RequestFailedException(
                f"Failed to get {url}, status code: {res.status_code} is not in {accepted_status}"
            )
        return res

    def get(self, url, accepted_status={200}, **kwargs) -> requests.Response:
        headers = self._get_updated_headers(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        res = self._retry(self._get, url=url, accepted_status=accepted_status, **kwargs)

        return res

    def _post(self, url, accepted_status={200}, **kwargs):
        res = requests.post(url, proxies=self.proxies, **kwargs)
        if res.status_code not in accepted_status:
            logger.warn(f"Failed to post {url}, status code: {res.status_code}")
            raise RequestFailedException(
                f"Failed to get {url}, status code: {res.status_code} is not in {accepted_status}"
            )
        return res

    def post(self, url, accepted_status={200}, **kwargs) -> requests.Response:
        headers = self._get_updated_headers(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        res = self._retry(
            self._post, url=url, accepted_status=accepted_status, **kwargs
        )

        return res
