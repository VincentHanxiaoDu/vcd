from vcd.utils.http import HttpClient
import time
import random
import re
from hashlib import sha1
from seleniumbase import Driver


class YoutubeVideoUploader:
    def __init__(self, driver) -> None:
        # self.driver = Driver(uc_cdp=True, headless=headless)
        self.driver = driver

    def upload(self, file, title, desc):
        try:
            self.driver.get("https://studio.youtube.com/")
            
            upload_btn = self.driver.wait_for_element_visible('[id="upload-button"]', timeout=10)
            upload_btn.click()
            # select_file_btn = self.driver.wait_for_element_visible('[id="select-files-button"]', timeout=10)
            # select_file_btn.click()
            file_input = self.driver.wait_for_selector('input[type="file"]', timeout=10)
            file_input.send_keys(file)
            
            title_input = self.driver.wait_for_selector('[id="title-textarea"]', timeout=10)
            title_input.clear()
            title_input.send_keys(title)
            desc_input = self.driver.wait_for_selector('[id="description-textarea"]', timeout=10)
            title_input.clear()
            desc_input.send_keys(desc)
        finally:
            self.driver.close()
            


    # def get_challenge_info(self):
    #     body = {
    #         "engagementType": "ENGAGEMENT_TYPE_UNBOUND",
    #         "context": {
    #             "client": {
    #                 "clientName": 62,
    #                 "clientVersion": "1.20240728.03.00",
    #                 "hl": "en",
    #                 "gl": "US",
    #                 "experimentsToken": "",
    #                 "utcOffsetMinutes": 480,
    #             },
    #             "request": {
    #                 "returnLogEntry": True,
    #                 "internalExperimentFlags": [],
    #                 "consistencyTokenJars": [],
    #             },
    #             "user": {
    #                 "delegationContext": {
    #                     "externalChannelId": self._info["channel_id"],
    #                     "roleType": {
    #                         "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
    #                     },
    #                 },
    #                 "serializedDelegationContext": self._info["delegate_context"],
    #             },
    #             "clientScreenNonce": "S0Jw_7Ko7WbR4Ucq",
    #         },
    #     }
    #     res = self._http_client.post(
    #         "https://studio.youtube.com/youtubei/v1/att/get?alt=json&key="
    #         + self._info["innertube_api_key"],
    #         headers={
    #             "content-type": "application/json",
    #         },
    #         cookies=self.cookies,
    #         json=body,
    #     )
    #     return res.json()


    # def get_challenge_info(self):
    #     body = {
    #         "engagementType": "ENGAGEMENT_TYPE_UNBOUND",
    #         "context": {
    #             "client": {
    #                 "clientName": 62,
    #                 "clientVersion": "1.20240728.03.00",
    #                 "hl": "en",
    #                 "gl": "US",
    #                 "experimentsToken": "",
    #                 "utcOffsetMinutes": 480,
    #             },
    #             "request": {
    #                 "returnLogEntry": True,
    #                 "internalExperimentFlags": [],
    #                 "consistencyTokenJars": [],
    #             },
    #             "user": {
    #                 "delegationContext": {
    #                     "externalChannelId": self._info["channel_id"],
    #                     "roleType": {
    #                         "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
    #                     },
    #                 },
    #                 "serializedDelegationContext": self._info["delegate_context"],
    #             },
    #             "clientScreenNonce": "S0Jw_7Ko7WbR4Ucq",
    #         },
    #     }
    #     res = self._http_client.post(
    #         "https://studio.youtube.com/youtubei/v1/att/get?alt=json&key="
    #         + self._info["innertube_api_key"],
    #         headers={
    #             "content-type": "application/json",
    #         },
    #         cookies=self.cookies,
    #         json=body,
    #     )
    #     return res.json()

    # def upload_video_meta(
    #     self,
    #     title,
    #     description,
    #     privacy,
    #     scotty_resource_id,
    #     is_draft=False,
    #     is_short=False,
    # ):
    #     channel_id = self._info["channel_id"]
    #     challenge = self.get_challenge_info()["challenge"]

    #     body = {
    #         "channelId": channel_id,
    #         "resourceId": {"scottyResourceId": {"id": scotty_resource_id}},
    #         "frontendUploadId": f"innertube_studio:{self.generate_hash()}:0",
    #         "initialMetadata": {
    #             "title": {"newTitle": title},
    #             "privacy": {"newPrivacy": privacy},
    #             "draftState": {"isDraft": is_draft},
    #             "description": {"newDescription": description, "shouldSegment": True},
    #         },
    #         "context": {
    #             "client": {
    #                 "clientName": 62,
    #                 "clientVersion": "1.20240723.03.00",
    #                 "hl": "en",
    #                 "gl": "US",
    #                 "experimentsToken": "",
    #                 "utcOffsetMinutes": 480,
    #                 "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
    #                 "screenWidthPoints": 739,
    #                 "screenHeightPoints": 824,
    #                 "screenPixelDensity": 2,
    #                 "screenDensityFloat": 2,
    #             },
    #             "request": {
    #                 "returnLogEntry": True,
    #                 "internalExperimentFlags": [],
    #                 "eats": "Ad7a0EGnAqTzSFyd74t6trKyhuaNXQXaOm3OGpTQYVnRY4fZfOziCzLVmOFAZzL2au2bHGMOleCisfX1dCzfPgthzXK_1Z1DSEoXjhRtmp889I4fFsbwgwPMqOXjoA==",
    #                 "attestationResponseData": {
    #                     "challenge": challenge,
    #                     "webResponse": "",
    #                 },
    #                 "sessionInfo": {"token": self.cookies["SESSION_TOKEN"]},
    #                 "consistencyTokenJars": [
    #                     {"encryptedTokenJarContents": "", "expirationSeconds": "600"}
    #                 ],
    #                 "returnLogEntry": True,
    #                 "internalExperimentFlags": [],
    #                 "sessionInfo": {"token": self.cookies["SESSION_TOKEN"]},
    #             }
    #     res = self._http_client.post(
    #         f"https://studio.youtube.com/youtubei/v1/upload/createvideo?alt=json&key={self._info['innertube_api_key']}",
    #         cookies=self.cookies,
    #         json=body,
    #     )
    #     print(res.json())
    #     return res
