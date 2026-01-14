import tempfile
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()

try:
    import whisper
except ImportError:
    whisper = None


class AudioTranscriber:
    def __init__(self, model_size: str = "base"):
        self.model = None
        self.model_size = model_size
        self._load_model()

    def _load_model(self):
        if not whisper:
            logger.warning("whisper_not_installed")
            return
        try:
            self.model = whisper.load_model(self.model_size)
            logger.info("whisper_model_loaded", model_size=self.model_size)
        except Exception as e:
            logger.error("whisper_load_failed", error=str(e))

    def download_audio(self, url: str, output_path: Path) -> bool:
        try:
            with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as response:
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            logger.info("audio_downloaded", path=str(output_path))
            return True
        except Exception as e:
            logger.error("audio_download_failed", url=url, error=str(e))
            return False

    def transcribe_file(self, audio_path: Path) -> Optional[dict]:
        if not self.model:
            logger.error("no_whisper_model")
            return None

        try:
            result = self.model.transcribe(
                str(audio_path),
                language="en",
                verbose=False,
            )
            return {
                "text": result["text"],
                "segments": [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                    }
                    for seg in result.get("segments", [])
                ],
            }
        except Exception as e:
            logger.error("transcription_failed", path=str(audio_path), error=str(e))
            return None

    def transcribe_url(self, audio_url: str) -> Optional[dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.mp3"
            if not self.download_audio(audio_url, audio_path):
                return None
            return self.transcribe_file(audio_path)

    def transcribe_youtube(self, video_id: str) -> Optional[dict]:
        try:
            import yt_dlp
        except ImportError:
            logger.error("yt_dlp_not_installed")
            return None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "audio"
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": str(output_path),
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

                audio_file = output_path.with_suffix(".mp3")
                if audio_file.exists():
                    return self.transcribe_file(audio_file)

                for f in Path(tmpdir).glob("audio*"):
                    return self.transcribe_file(f)

                logger.error("audio_file_not_found", video_id=video_id)
                return None

        except Exception as e:
            logger.error("youtube_transcribe_failed", video_id=video_id, error=str(e))
            return None
