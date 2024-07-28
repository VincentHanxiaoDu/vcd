import os
import json
import google.auth
from vcd.platforms.youtube.auth import YouTubeOAuth2Client
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io


class YoutubeVideoUploader:
    def __init__(self) -> None:
        pass
