from vcd.utils.http import HttpClient
import time
import random
import re
from hashlib import sha1


class YoutubeVideoUploader:
    def __init__(self, cookies: dict, http_client: HttpClient) -> None:
        self.cookies = cookies
        self._http_client = http_client
        self._info = self.get_info()
        # self.auth = f"SAPISIDHASH {self.generate_sapisidhash(int(time.time() * 1000), self.cookies['SAPISID'])}",

    @staticmethod
    def generate_hash():
        qkb = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        a = [None] * 36
        b = 0

        for e in range(36):
            if e in (8, 13, 18, 23):
                a[e] = "-"
            elif e == 14:
                a[e] = "4"
            else:
                if b <= 2:
                    b = 33554432 + int(16777216 * random.random())
                c = b & 15
                b >>= 4
                a[e] = qkb[(c & 3 | 8) if e == 19 else c]
        return "".join(a)

    @staticmethod
    def generate_sapisidhash(ts_ms, sapisid):
        return f"{ts_ms}_{sha1(f'{ts_ms} {sapisid} https://studio.youtube.com'.encode()).hexdigest()}"

    def _get_upload_url(self):
        res = self._http_client.post(
            "https://upload.youtube.com/upload/studio?authuser=3",
            cookies=self.cookies,
            headers={
                # "authorization": self.auth,
                "content-type": "application/x-www-form-urlencoded;charset=utf-8",
                "x-goog-upload-command": "start",
                "x-goog-upload-file-name": "file-" + str(int(time.time() * 1000)),
                "x-goog-upload-protocol": "resumable",
                "Referer": "https://studio.youtube.com/",
            },
            json={"frontendUploadId": f"innertube_studio:{self.generate_hash()}:0"},
        )
        return res.headers["X-Goog-Upload-URL"]

    def get_info(self):
        res = self._http_client.get(
            "https://studio.youtube.com",
            cookies=self.cookies,
        )
        channel_id = re.search(r'"CHANNEL_ID":"(.*?)"', res.text).group(1)
        innertube_api_key = re.search(r'"INNERTUBE_API_KEY":"(.*?)"', res.text).group(1)
        delegate_context = re.search(
            r'"INNERTUBE_CONTEXT_SERIALIZED_DELEGATION_CONTEXT":"(.*?)"', res.text
        ).group(1)
        return {
            "channel_id": channel_id,
            "innertube_api_key": innertube_api_key,
            "delegate_context": delegate_context,
        }

    def upload(self, input_stream, scotty_resource_id_stateful):
        upload_url = self._get_upload_url()
        res = self._http_client.post(
            upload_url,
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=utf-8",
                "x-goog-upload-command": "upload, finalize",
                "x-goog-upload-file-name": "file-" + str(int(time.time() * 1000)),
                "x-goog-upload-offset": "0",
                "referrer": "https://studio.youtube.com/",
            },
            cookies=self.cookies,
            data=input_stream,
        )
        scotty_resource_id_stateful.set(res.json()["scottyResourceId"])

    def get_challenge_info(self):
        body = {
            "engagementType": "ENGAGEMENT_TYPE_UNBOUND",
            "context": {
                "client": {
                    "clientName": 62,
                    "clientVersion": "1.20240728.03.00",
                    "hl": "en",
                    "gl": "US",
                    "experimentsToken": "",
                    "utcOffsetMinutes": 480,
                },
                "request": {
                    "returnLogEntry": True,
                    "internalExperimentFlags": [],
                    "consistencyTokenJars": [],
                },
                "user": {
                    "delegationContext": {
                        "externalChannelId": self._info["channel_id"],
                        "roleType": {
                            "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
                        },
                    },
                    "serializedDelegationContext": self._info["delegate_context"],
                },
                "clientScreenNonce": "S0Jw_7Ko7WbR4Ucq",
            },
        }
        res = self._http_client.post(
            "https://studio.youtube.com/youtubei/v1/att/get?alt=json&key="
            + self._info["innertube_api_key"],
            headers={
                "content-type": "application/json",
            },
            cookies=self.cookies,
            json=body,
        )
        return res.json()

    def upload_video_meta(
        self,
        title,
        description,
        privacy,
        scotty_resource_id,
        is_draft=False,
        is_short=False,
    ):
        channel_id = self._info["channel_id"]
        challenge = self.get_challenge_info()["challenge"]

        body = {
            "channelId": channel_id,
            "resourceId": {"scottyResourceId": {"id": scotty_resource_id}},
            "frontendUploadId": f"innertube_studio:{self.generate_hash()}:0",
            "initialMetadata": {
                "title": {"newTitle": title},
                "privacy": {"newPrivacy": privacy},
                "draftState": {"isDraft": is_draft},
                "description": {"newDescription": description, "shouldSegment": True},
            },
            "context": {
                "client": {
                    "clientName": 62,
                    "clientVersion": "1.20240723.03.00",
                    "hl": "en",
                    "gl": "US",
                    "experimentsToken": "",
                    "utcOffsetMinutes": 480,
                    "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                    "screenWidthPoints": 739,
                    "screenHeightPoints": 824,
                    "screenPixelDensity": 2,
                    "screenDensityFloat": 2,
                },
                "request": {
                    "returnLogEntry": True,
                    "internalExperimentFlags": [],
                    "eats": "Ad7a0EGnAqTzSFyd74t6trKyhuaNXQXaOm3OGpTQYVnRY4fZfOziCzLVmOFAZzL2au2bHGMOleCisfX1dCzfPgthzXK_1Z1DSEoXjhRtmp889I4fFsbwgwPMqOXjoA==",
                    "attestationResponseData": {
                        "challenge": challenge,
                        "webResponse": "",
                    },
                    "sessionInfo": {"token": self.cookies["SESSION_TOKEN"]},
                    "consistencyTokenJars": [
                        {"encryptedTokenJarContents": "", "expirationSeconds": "600"}
                    ],
                    "returnLogEntry": True,
                    "internalExperimentFlags": [],
                    "sessionInfo": {"token": self.cookies["SESSION_TOKEN"]},
                },
                "user": {
                    "delegationContext": {
                        "externalChannelId": channel_id,
                        "roleType": {
                            "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
                        },
                    },
                    "serializedDelegationContext": self._info["delegate_context"],
                },
                "clientScreenNonce": "",
            },
            "delegationContext": {
                "externalChannelId": channel_id,
                "roleType": {"channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"},
            },
            "presumedShort": is_short,
            "kronosExperimentIds": [],
        }
        res = self._http_client.post(
            f"https://studio.youtube.com/youtubei/v1/upload/createvideo?alt=json&key={self._info['innertube_api_key']}",
            cookies=self.cookies,
            json=body,
        )
        return res
