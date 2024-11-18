import sqlite3
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from vcd.utils.stateful import Stateful
from vcd.utils.time import timer
from seleniumbase import Driver
import re
import base64
import json
from hashlib import sha1
import time


class YouTubeOAuth2Client:
    def __init__(
        self,
        cred_secret_json,
        scopes,
        db="cred.db",
        table="youtube_cred",
        server_port=8080,
        timeout=120,
    ):
        self.client_id = cred_secret_json["web"]["client_id"]
        self.session_uri = None
        self.db = db
        self.table = table
        self.scopes = scopes
        self.cred_secret_json = cred_secret_json
        self.server_port = server_port
        self.timeout = timeout
        self._init_cred_table()

    def _sql(self, sql, parameters=()):
        with sqlite3.connect(self.db) as conn:
            c = conn.cursor()
            res = c.execute(sql, parameters)
            conn.commit()
        return res

    def _init_cred_table(self):
        self._sql(
            f"CREATE TABLE IF NOT EXISTS {self.table} (client_id TEXT, cred_json TEXT)"
        )

    def _update_cred_cache(self, cred):
        self._sql(
            f"INSERT OR REPLACE INTO {self.table} (client_id, cred_json) VALUES (?, ?)",
            (self.client_id, cred.to_json()),
        )

    def _get_cached_cred(self):
        cred_json = self._sql(
            sql=f"SELECT cred_json FROM {self.table} WHERE client_id = ?",
            parameters=(self.client_id,),
        ).fetchone()
        if not cred_json:
            return None
        try:
            auth_info = json.loads(cred_json[0])
            return Credentials.from_authorized_user_info(auth_info, scopes=self.scopes)
        except (json.JSONDecodeError, AttributeError):
            self._sql("DELETE FROM ? WHERE client_id = ?", parameters=(self.client_id,))
            return None

    def _get_new_cred(self):
        flow = InstalledAppFlow.from_client_config(self.cred_secret_json, self.scopes)
        cred = flow.run_local_server(
            port=self.server_port, timeout_seconds=self.timeout
        )
        return cred

    def get_cred(self):
        cred = self._get_cached_cred()
        if not cred:
            cred = self._get_new_cred()
        if cred and not cred.valid and cred.refresh_token:
            cred.refresh(Request())
        self._update_cred_cache(cred)
        return cred


class YouTubeAuthClient:
    def __init__(self, username_b64=None, password_b64=None) -> None:
        self._username_b64 = username_b64
        self._password_b64 = password_b64
        self._has_credential = self._username_b64 and self._password_b64

    @property
    def username(self):
        return base64.b64decode(self._username_b64).decode("utf-8")

    @property
    def password(self):
        return base64.b64decode(self._password_b64).decode("utf-8")

    @staticmethod
    def build_session_token_func(driver, session_token_stateful):
        def extract_session_token(data):
            # print(data)
            
            url = data.get("params", {}).get("response", {}).get("url", "")
            if re.match(r"https://studio.youtube.com/youtubei/v1/att/esr", url):
                request_id = data.get("params", {}).get("requestId")
                if request_id is not None:
                    session_token_stateful.set(
                        json.loads(
                            driver.execute_cdp_cmd(
                                "Network.getResponseBody", {"requestId": request_id}
                            )["body"]
                        )["ctx"]
                    )
        return extract_session_token
    
    def login_driver(self, headless=False):
        try:
            driver = Driver(uc_cdp=True, headless=headless)
            session_token_stateful = Stateful()
            extract_session_token = self.build_session_token_func(
                driver, session_token_stateful
            )
            driver.add_cdp_listener("Network.responseReceived", extract_session_token)
            # driver.uc_open_with_reconnect("https://studio.youtube.com", 3)
            driver.get("https://studio.youtube.com")
            if self._has_credential:
                driver.wait_for_element_visible(
                    'input[type="email"]', timeout=10
                ).send_keys(self.username)
                driver.wait_for_element_visible(
                    '//button[.//span[text()="Next"]]', by="xpath"
                ).click()
                driver.wait_for_element_visible(
                    'input[type="password"]', timeout=10
                ).send_keys(self.password)
                driver.wait_for_element_visible(
                    '//button[.//span[text()="Next"]]', by="xpath"
                ).click()
            return driver, session_token_stateful
        except Exception as e:
            driver.quit()
            raise e

    def get_cookies(self, timeout=120):
        headless = False
        if self._has_credential:
            headless = True
        cookies = Stateful()            
            
        while True:
            cookies = {
                c["name"]: c["value"]
                for c in filter(
                    lambda x: x["domain"] == ".youtube.com", driver.get_cookies()
                )
            }
            if required_cookies.issubset(cookies.keys()):
                cookies = {k: v for k, v in cookies.items() if k in required_cookies}
                break
            if is_timeout():
                raise TimeoutError()
            time.sleep(1)
        driver.quit()
        return {**cookies, "SESSION_TOKEN": session_token}
