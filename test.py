from vcd.platforms.youtube.upload import YoutubeVideoUploader
from vcd.platforms.youtube.auth import YouTubeAuthClient
from vcd.utils.stateful import Stateful
from vcd.utils.stream import WriteableQueue
import json

from vcd.utils.http import HttpClient

if __name__ == "__main__":
    auth = YouTubeAuthClient(username_b64="", password_b64="")
    # cookies = auth.get_cookies(timeout=120)
    
    # with open("cookies.json", "w") as f:
    #     json.dump(cookies, f)
        
    # with open("cookies.json", "r") as f:
    #     cookies = json.load(f)

    # http_client = HttpClient(
    #     headers={
    #         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    #     },
    #     proxies=None
    # )
    
    driver, _ = auth.login_driver(headless=False)
    uploader = YoutubeVideoUploader(driver)

    # with open("/home/hanxiaodu/Desktop/vcd/test.mp4", "rb") as f:
    
    uploader.upload("/home/hanxiaodu/Desktop/vcd/test.mp4")
        # print(scotty_resource_id_stateful.get())
        
        # uploader.upload_video_meta(
        #     title="test",
        #     description="test",
        #     privacy="PRIVATE",
        #     scotty_resource_id=scotty_resource_id_stateful.get()
        # )
        
        
