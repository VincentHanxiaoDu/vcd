from vcd.platforms.youtube.video_info import YoutubeVideoInfo
from vcd.utils.http import HttpClient
import subprocess
import os
import shlex
import threading
import logging

logger = logging.getLogger(__name__)


class YoutubeVideoDownloader:
    def __init__(
        self,
        youtube_video_info: YoutubeVideoInfo,
        http_client: HttpClient,
        ffmpeg_path="tools/ffmpeg",
    ) -> None:
        self._http_client = http_client
        self._yvi = youtube_video_info
        self._ffmpeg_path = ffmpeg_path

    @staticmethod
    def save_pipe(file_name, stream_out):
        output = 0
        with open(file_name, "wb") as f:
            while True:
                chunk = stream_out.read(1024000)
                if chunk == b"":
                    break
                output += 1024000
                f.write(chunk)
                logger.info(f"Output: {output}")

    def feed_pipe(self, url, write_fd, chunk_size=65536):
        with self._http_client.get(url, stream=True) as res:
            with os.fdopen(write_fd, "wb", closefd=True) as pipe:
                cl = int(res.headers.get("Content-Length", -1))
                downloaded = 0
                for chunk in res.iter_content(chunk_size=chunk_size):
                    if chunk:
                        curr_chunk_size = len(chunk)
                        downloaded += curr_chunk_size
                        if (
                            downloaded % (chunk_size * 10) == 0
                            or curr_chunk_size < chunk_size
                        ):
                            logger.info(
                                f"Downloaded {downloaded}/{cl}({int(downloaded/cl * 100)}%)"
                            )
                        pipe.write(chunk)

    def merged_stream(self):
        video_stream_info = self._yvi.video_formats[0]
        audio_stream_info = self._yvi.audio_formats[0]
        video_read_fd, video_write_fd = os.pipe()
        audio_read_fd, audio_write_fd = os.pipe()
        command = f"{self._ffmpeg_path} -y -f {video_stream_info['mime_info']['ext']} -i pipe:{video_read_fd} -i pipe:{audio_read_fd} -c:v copy -c:a aac -f flv -flvflags no_duration_filesize -"
        # command = f"{self._ffmpeg_path} -y -f {video_stream_info['mime_info']['ext']} -i pipe:{video_read_fd} -i pipe:{audio_read_fd} -c:v copy -c:a aac -f mpegts -"
        process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=(video_read_fd, audio_read_fd),
        )

        video_pipe_thread = threading.Thread(
            target=self.feed_pipe,
            args=(video_stream_info["decrypted_url"], video_write_fd),
        )
        audio_pipe_thread = threading.Thread(
            target=self.feed_pipe,
            args=(audio_stream_info["decrypted_url"], audio_write_fd),
        )

        video_pipe_thread.start()
        audio_pipe_thread.start()

        output = 0
        try:
            while True:
                chunk = process.stdout.read(1024000)
                if chunk == b"":
                    break
                output += 1024000
                logger.info(f"Output: {output}")
                yield chunk
        finally:
            video_pipe_thread.join()
            audio_pipe_thread.join()
