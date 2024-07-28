from vcd.utils.http import HttpClient, RequestFailedException
from vcd.utils.transformations import get_index, nvl
from vcd.utils.cache import Cacheable
from vcd.utils.url import URL
from typing import Optional
import json
import logging
import urllib
import execjs
import vcd.utils.format as format_utils
import m3u8
import re
import functools


logger = logging.getLogger(__name__)


class GetInfoFailedException(Exception):
    pass


class TrailerVideoException(GetInfoFailedException):
    def __init__(self, video_id, trailer_video_id) -> None:
        self.video_id = video_id
        self.trailer_video_id = trailer_video_id
        super().__init__(
            f"Trailer video found for video {video_id}: {trailer_video_id}"
        )


class YoutubeVideoInfo(Cacheable):
    def __init__(self, video_id, http_client: HttpClient, allow_cache=True) -> None:
        super().__init__(allow_cache=allow_cache)
        self.video_id = video_id
        self.http_client = http_client

    @property
    @Cacheable.cache
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}&bpctr=9999999999&has_verified=1"

    @property
    @Cacheable.cache
    def watch_page_src(self):
        try:
            res = self.http_client.get(self.watch_url, accepted_status={200})
            return res.text
        except RequestFailedException:
            logger.warn(f"Failed to get watch page with watch url: {self.watch_url}")
            return None

    _PLAYER_RESPONSE_RE = re.compile(
        r"ytInitialPlayerResponse\s*=\s*({.+?})\s*;(?:var\s+meta|</script|\n)"
    )

    @property
    @Cacheable.cache
    def player_info_from_watch_page(self):
        player_response = self._PLAYER_RESPONSE_RE.search(self.watch_page_src)
        if not player_response:
            logger.warn(
                f"Failed to get player response from watch page with watch url: {self.watch_url}"
            )
            return None
        player_response_match = player_response.group(1)
        try:
            return json.loads(player_response_match)
        except json.JSONDecodeError:
            logger.warn(
                f"Failed to parse player response from watch page with watch url: {self.watch_url}"
            )
            return None

    _PLAYER_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

    def _fetch_player_info_from_api(
        self, json_payload: dict, headers: Optional[dict] = None
    ):
        res = self.http_client.post(
            f"https://www.youtube.com/youtubei/v1/player?key={self._PLAYER_API_KEY}",
            json=json_payload,
            headers=headers,
            accepted_status={200},
        )
        try:
            return res.json()
        except json.JSONDecodeError:
            logger.warn(
                f"Failed to get player info from api with video id: {self.video_id}"
            )
            return None

    @property
    @Cacheable.cache
    def player_info_from_api(self):
        json_payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20201021.03.00",
                }
            },
            "videoId": self.video_id,
        }
        return self._fetch_player_info_from_api(json_payload=json_payload)

    _PLAYER_JS_RE = re.compile(r"\"(?:PLAYER_JS_URL|jsUrl)\"\s*:\s*\"([^\"]+)\"")

    @property
    @Cacheable.cache
    def player_js_url(self):
        player_js = self._PLAYER_JS_RE.search(self.watch_page_src)
        if player_js:
            return urllib.parse.urljoin("https://www.youtube.com", player_js.group(1))

    @property
    @Cacheable.cache
    def player_js_src(self):
        if self.player_js_url is None:
            return None
        try:
            res = self.http_client.get(self.player_js_url)
            return res.text
        except RequestFailedException:
            pass

    _YTCFG_RE = re.compile(r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;")

    @property
    @Cacheable.cache
    def yt_cfg(self):
        yt_cfg_search = self._YTCFG_RE.search(self.watch_page_src)
        if not yt_cfg_search:
            return None
        try:
            return json.loads(yt_cfg_search.group(1))
        except json.JSONDecodeError:
            return None

    _SIS_RE = re.compile(r"(?:signatureTimestamp|sts)\s*:\s*(?P<sts>[0-9]{5})")

    @property
    @Cacheable.cache
    def sts(self) -> Optional[int]:
        if self.yt_cfg is not None and "STS" in self.yt_cfg:
            return int(self.yt_cfg["STS"])
        sis_search = self._SIS_RE.search(self.player_js_src)
        if sis_search:
            return int(sis_search.group("sts"))

    @property
    @Cacheable.cache
    def unrestricted_player_info(self):
        pb_context = {"html5Preference": "HTML5_PREF_WANTS"}
        if self.sts is not None:
            pb_context["signatureTimestamp"] = self.sts
        json_payload = {
            "playbackContext": {"contentPlaybackContext": pb_context},
            "contentCheckOk": True,
            "racyCheckOk": True,
            "context": {
                "client": {
                    "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                    "clientVersion": "2.0",
                    "hl": "en",
                    "clientScreen": "EMBED",
                },
                "thirdParty": {"embedUrl": "https://google.com"},
            },
            "videoId": self.video_id,
        }

        headers = {
            "X-YouTube-Client-Name": "85",
            "X-YouTube-Client-Version": "2.0",
            "Origin": "https://www.youtube.com",
        }

        player_info = self._fetch_player_info_from_api(
            json_payload=json_payload, headers=headers
        )
        if self._is_age_restricted(player_info) or not self._is_playable(player_info):
            logger.error(
                f"Failed to get unrestricted player info for video {self.video_id}"
            )
            raise GetInfoFailedException(
                f"Failed to get unrestricted player info for video {self.video_id}"
            )
        return player_info

    @staticmethod
    def _is_age_restricted(player_info):
        return "desktopLegacyAgeGateReason" in player_info.get("playabilityStatus", {})

    @staticmethod
    def _is_playable(player_info):
        return player_info.get("playabilityStatus", {}).get("status") == "OK"

    @staticmethod
    def _get_tailer_video_id(player_info):
        return (
            player_info.get("playabilityStatus", {})
            .get("errorScreen", {})
            .get("playerLegacyDesktopYpcTrailerRenderer", {})
            .get("trailerVideoId")
        )

    @property
    @Cacheable.cache
    def player_info(self):
        original_player_info = (
            self.player_info_from_watch_page or self.player_info_from_api
        )
        if self._is_playable(original_player_info):
            return original_player_info

        tailer_video_id = self._get_tailer_video_id(original_player_info)
        if tailer_video_id is not None:
            raise TrailerVideoException(self.video_id, tailer_video_id)
        elif self._is_age_restricted(original_player_info):
            return self.unrestricted_player_info
        else:
            logger.error(
                f"Unknown playability status for video {self.video_id}: {original_player_info.get('playabilityStatus', {}).get('status')}"
            )
            return original_player_info

    @property
    @Cacheable.cache
    def video_details(self):
        if self.player_info is None:
            return None
        return self.player_info.get("videoDetails", {})

    @property
    @Cacheable.cache
    def micro_format(self):
        if self.player_info is None:
            return None
        return self.player_info.get("microformat", {})

    @property
    @Cacheable.cache
    def micro_format_renderer(self):
        if self.micro_format is None:
            return None
        return self.micro_format.get("playerMicroformatRenderer", {})

    _TITLE_RE = re.compile(
        r"(?isx)<meta(?=[^>]+(?:itemprop|name|property|id|http-equiv)=([\"\']?)(?:og:title|twitter:title|title)\1)[^>]+?content=([\"\'])(?P<content>.*?)\2"
    )

    @property
    @Cacheable.cache
    def title(self):
        if self.video_details is None:
            return None
        return (
            self.video_details.get("title")
            or self.micro_format_renderer.get("microformat")
            or self._TITLE_RE.search(self.watch_page_src).group("content")
        )

    @property
    @Cacheable.cache
    def video_description(self):
        if self.video_details is None:
            return None
        return self.video_details.get("shortDescription")

    _PLAYER_ID_RES = (
        re.compile(r"/s/player/(?P<id>[a-zA-Z0-9_-]{8,})/player"),
        re.compile(
            r"/(?P<id>[a-zA-Z0-9_-]{8,})/player(?:_ias\.vflset(?:/[a-zA-Z]{2,3}_[a-zA-Z]{2,3})?|-plasma-ias-(?:phone|tablet)-[a-z]{2}_[A-Z]{2}\.vflset)/base\.js$"
        ),
        re.compile(r"\b(?P<id>vfl[a-zA-Z0-9_-]+)\b.*?\.js$"),
    )

    @property
    @Cacheable.cache
    def player_id(self):
        if self.player_js_url is None:
            return None
        for res in self._PLAYER_ID_RES:
            match = res.search(self.player_js_url)
            if match:
                return match.group("id")

    _JS_DECRYPT_FUNC_META_RE = regex = re.compile(
        r"""
        (?x)
        (?:\(\s*(?P<b>[a-z])\s*=\s*(?:String\s*\.\s*fromCharCode\s*\(\s*110\s*\)|\"n+\"\[\s*\+?s*[\w$.]+\s*]
        )\s*,(?P<c>[a-z])\s*=\s*[a-z]\s*)?
        \.\s*get\s*\(\s*(?(b)(?P=b)|\"n{1,2}\")(?:\s*\)){2}\s*&&\s*\(\s*(?(c)(?P=c)|b)\s*=\s*(?P<var>[a-zA-Z_$][\w$]*)(?:\s*\[(?P<idx>\d+)\])?\s*\(\s*[\w$]+\s*\)
        """
    )

    @property
    @Cacheable.cache
    def _decrypt_n_js_func(self):
        js_decrypt_func_meta_search = self._JS_DECRYPT_FUNC_META_RE.search(
            self.player_js_src
        )

        func_array_var = js_decrypt_func_meta_search.group("var")
        idx = js_decrypt_func_meta_search.group("idx")
        if func_array_var is None or idx is None:
            return None
        func_names_list_search = re.search(
            rf"var {re.escape(func_array_var)}\s*=\s*\[(.+?)\]\s*[,;]",
            self.player_js_src,
        )
        func_names_list = [
            i.strip() for i in func_names_list_search.group(1).split(",")
        ]
        decrypt_func_name = re.escape(func_names_list[int(idx)])
        func_search = re.search(
            rf"{decrypt_func_name}=function(?:.|\n)*?}};\n",
            self.player_js_src,
            re.MULTILINE,
        )
        js = execjs.compile(func_search.group(0))
        return functools.partial(js.call, decrypt_func_name)

    def _get_decrypted_foramt_url(self, format_url):
        if not format_url:
            return None
        url = URL(format_url)
        n = url.query_dict.get("n")
        if n is None:
            return format_url
        query_dict = url.query_dict
        query_dict["n"] = self._decrypt_n_js_func(n)
        updated_url = url.with_query_updated(query_dict)
        return updated_url.url

    _MIME_TYPE_RE = re.compile(
        r"((?P<type>[^/]+)/(?P<ext>[^;]+))(?:;\s*codecs=\"(?P<codec>[^\"]+)\")?"
    )

    @property
    @Cacheable.cache
    def streaming_data(self):
        if self.player_info is None:
            return None
        return self.player_info.get("streamingData", {})

    _SPEC_JS = execjs.compile(
        """
        var iL={
            AY:function(a,b){a.splice(0,b)},
            T8:function(a){a.reverse()},
            Kq:function(a,b){var c=a[0];a[0]=a[b%a.length];a[b%a.length]=c}
        };

        getSpec=function(a){a=a.split("");iL.AY(a,1);iL.T8(a,60);iL.Kq(a,51);iL.T8(a,44);iL.AY(a,3);iL.T8(a,63);iL.Kq(a,35);return a.join("")};
        """
    )

    @classmethod
    def _get_decrypted_format_url_from_cipher(cls, sign_cipher: str):
        info = dict(map(lambda x: x.split("="), sign_cipher.split("&")))
        encrypted_sig = info["s"]
        test_string = "".join(map(chr, range(len(encrypted_sig))))
        spec = [ord(c) for c in cls._SPEC_JS.call("getSpec", test_string)]
        sign = "".join(encrypted_sig[i] for i in spec)
        url = URL(info["url"])
        query_dict = url.query_dict
        query_dict[info.get("sig", "signature")] = sign
        return url.with_query_updated(query_dict).url

    _QUALITY_PREF = [
        "tiny",
        "small",
        "medium",
        "large",
        "hd720",
        "hd1080",
        "hd1440",
        "hd2160",
        "hd2880",
        "highres",
    ]
    _AUDIO_QUALITY_PREF = [
        "AUDIO_QUALITY_LOW",
        "AUDIO_QUALITY_MEDIUM",
        "AUDIO_QUALITY_HIGH",
    ]

    @classmethod
    def _sort_adaptive_formats(cls, adaptive_formats):
        def _sort_key(format):
            return (
                nvl(get_index(cls._QUALITY_PREF, format.get("quality")), -1),
                nvl(format.get("fps"), -1),
                nvl(
                    get_index(cls._AUDIO_QUALITY_PREF, format.get("audio_quality")), -1
                ),
                nvl(format.get("bitrate"), -1),
            )

        return sorted(adaptive_formats, key=_sort_key, reverse=True)

    @property
    @Cacheable.cache
    def _adaptive_formats(self):
        if self.streaming_data is None:
            return None
        adaptive_formats = format_utils.to_snake_case(
            self.streaming_data.get("adaptiveFormats", [])
        )

        formats = []

        for format in adaptive_formats:
            format["decrypted_url"] = self._get_decrypted_foramt_url(
                format.get("url")
            ) or self._get_decrypted_format_url_from_cipher(
                format.get("signatureCipher")
            )
            mime_info_search = self._MIME_TYPE_RE.search(format["mime_type"])
            format["mime_info"] = {
                "type": mime_info_search.group("type"),
                "ext": mime_info_search.group("ext"),
                "codec": mime_info_search.group("codec"),
            }
            if not format.get("drmFamilies"):
                formats.append(format)
        return formats

    @property
    @Cacheable.cache
    def adaptive_formats(self, retry_times=3):
        formats = self._adaptive_formats
        while retry_times > 0:
            try:
                assert len(formats) > 0
                self.http_client.get(
                    formats[0]["decrypted_url"], accepted_status={200}, stream=True
                )
                break
            except (RequestFailedException, AssertionError):
                retry_times -= 1
                self.clear_cache()
                formats = self._adaptive_formats
        if retry_times <= 0:
            raise GetInfoFailedException("Failed to get adaptive formats")

        return {
            "video": self._sort_adaptive_formats(
                filter(lambda x: x["mime_info"]["type"] == "video", formats)
            ),
            "audio": self._sort_adaptive_formats(
                filter(lambda x: x["mime_info"]["type"] == "audio", formats)
            ),
        }

    @property
    @Cacheable.cache
    def video_formats(self):
        if self.adaptive_formats is None:
            return None
        return self.adaptive_formats.get("video")

    @property
    @Cacheable.cache
    def audio_formats(self):
        if self.adaptive_formats is None:
            return None
        return self.adaptive_formats.get("audio")

    @property
    @Cacheable.cache
    def is_live_content(self):
        if self.video_details is None:
            return None
        return self.video_details.get("isLiveContent")

    @property
    @Cacheable.cache
    def hls_manifest_u3m8(self):
        # Live stream.
        if self.streaming_data is None:
            return None
        manifest_url = self.streaming_data.get("hlsManifestUrl")
        try:
            res = self.http_client.get(manifest_url, accepted_status={200})
        except RequestFailedException:
            logger.warn(f"Failed to get live stream manifest with url: {manifest_url}")
            return None
        return m3u8.parse(res.text)

    @property
    @Cacheable.cache
    def playable(self):
        if self.streaming_data is not None and self.streaming_data.get("licenseInfos"):
            return False
        if self.player_info is not None and self._is_playable(self.player_info):
            return False
        return True

    @property
    @Cacheable.cache
    def thumbnails(self):
        if self.video_details is None:
            return []
        return self.video_details.get("thumbnail", {}).get("thumbnails", [])

    @property
    @Cacheable.cache
    def category(self):
        if self.micro_format_renderer is None:
            return None
        return self.video_details.get("category")
