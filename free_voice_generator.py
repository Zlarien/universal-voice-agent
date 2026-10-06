"""
Free Voice Generator - 3-Level TTS Fallback System
Level 1: FakeYou (community voice models)
Level 2: YouTube + XTTS zero-shot clone (HuggingFace)
Level 3: gTTS (Google Text-to-Speech)
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
import logging
from typing import Optional

import requests
from gtts import gTTS
import yt_dlp

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Language mapping for gTTS fallback
LANG_MAP: dict[str, str] = {
    "fr": "fr", "en": "en", "es": "es", "de": "de",
    "it": "it", "pt": "pt", "ja": "ja", "ko": "ko",
    "zh": "zh-CN", "ar": "ar", "ru": "ru",
}


class VoiceGenerator:
    """Generates speech audio using a 3-level fallback architecture."""

    def __init__(self, output_dir: str = "output", language: str = "fr") -> None:
        self.output_dir = output_dir
        self.language = language
        os.makedirs(self.output_dir, exist_ok=True)
        self._fakeyou_models: Optional[list[dict]] = None
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Level 1 — FakeYou
    # ------------------------------------------------------------------

    def _fetch_fakeyou_models(self) -> list[dict]:
        """Fetch and cache the full list of FakeYou voice models."""
        if self._fakeyou_models is not None:
            return self._fakeyou_models
        logger.info("Fetching FakeYou voice models...")
        try:
            res = self._session.get(
                "https://api.fakeyou.com/tts/list", timeout=15
            )
            res.raise_for_status()
            data = res.json()
            if data.get("success"):
                self._fakeyou_models = data.get("models", [])
                logger.info(
                    f"Loaded {len(self._fakeyou_models)} models from FakeYou."
                )
                return self._fakeyou_models
        except Exception as exc:
            logger.error(f"Error fetching FakeYou models: {exc}")
        return []

    def _search_model(self, name: str) -> Optional[dict]:
        """Search for a model whose title contains *name*."""
        models = self._fetch_fakeyou_models()
        name_lower = name.lower()
        matches = [
            m for m in models if name_lower in m.get("title", "").lower()
        ]
        return matches[0] if matches else None

    def _generate_fakeyou(
        self, text: str, model_token: str, output_path: str
    ) -> bool:
        """Submit a TTS job to FakeYou and poll until completion."""
        logger.info("Level 1: FakeYou TTS generation...")
        payload = {
            "tts_model_token": model_token,
            "uuid_idempotency_token": str(uuid.uuid4()),
            "inference_text": text,
        }
        try:
            res = self._session.post(
                "https://api.fakeyou.com/tts/inference",
                json=payload,
                timeout=15,
            )
            res.raise_for_status()
            data = res.json()
            if not data.get("success"):
                return False

            job_token = data.get("inference_job_token")
            logger.info("Job started. Waiting in queue...")

            for _ in range(30):  # max wait ~90 s
                time.sleep(3)
                poll = self._session.get(
                    f"https://api.fakeyou.com/tts/job/{job_token}", timeout=10
                )
                poll.raise_for_status()
                poll_data = poll.json()
                if not poll_data.get("success"):
                    return False

                status = poll_data.get("state", {}).get("status")
                if status == "complete_success":
                    audio_path = poll_data["state"].get(
                        "maybe_public_bucket_wav_audio_path"
                    )
                    if not audio_path:
                        return False
                    audio_url = f"https://storage.fakeyou.com{audio_path}"
                    audio_res = self._session.get(audio_url, timeout=30)
                    audio_res.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(audio_res.content)
                    return True
                elif status in ("complete_failure", "dead"):
                    return False
            return False
        except Exception as exc:
            logger.error(f"FakeYou exception: {exc}")
            return False

    # ------------------------------------------------------------------
    # Level 2 — YouTube reference audio + XTTS zero-shot clone
    # ------------------------------------------------------------------

    def _get_youtube_reference_audio(
        self, name: str, temp_dir: str
    ) -> Optional[str]:
        """Download a 15-second audio clip from mid-video to maximise
        the chance that it is the target speaker (skip the intro)."""
        logger.info("Level 2: Fetching reference audio from YouTube...")
        ydl_opts: dict = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": os.path.join(temp_dir, "ref_audio.%(ext)s"),
            # Extract 15 s starting at 1 min to skip journalist intros
            "download_ranges": yt_dlp.utils.download_range_func(
                None, [(60, 75)]
            ),
            "quiet": True,
            "no_warnings": True,
        }

        query = f"ytsearch1:{name} discours allocution officielle"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])

            # Locate the extracted file (extension may vary)
            for fname in os.listdir(temp_dir):
                if fname.startswith("ref_audio"):
                    path = os.path.join(temp_dir, fname)
                    logger.info("Successfully downloaded 15 s reference audio.")
                    return path
        except Exception as exc:
            logger.error(f"Error fetching YouTube audio: {exc}")
        return None

    def _generate_xtts_clone(
        self, text: str, reference_audio: str, output_path: str
    ) -> bool:
        """Call the public XTTS HuggingFace Space for zero-shot cloning."""
        logger.info("Calling HuggingFace XTTS Space for cloning...")
        try:
            from gradio_client import Client

            client = Client("coqui/xtts")
            result = client.predict(
                text=text,
                language=self.language,
                speaker_audio=reference_audio,
                api_name="/predict",
            )
            # Result is either a path string or a tuple containing a path
            gen_path: str = result[0] if isinstance(result, tuple) else result
            shutil.move(gen_path, output_path)
            return True
        except Exception as exc:
            logger.error(f"XTTS Generation failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Level 3 — gTTS fallback
    # ------------------------------------------------------------------

    def _generate_fallback(
        self, text: str, output_path: str
    ) -> tuple[bool, Optional[str]]:
        """Generate speech with Google TTS (always available)."""
        logger.info("Level 3: gTTS fallback...")
        try:
            lang = LANG_MAP.get(self.language, "fr")
            tts = gTTS(text=text, lang=lang)
            base, _ = os.path.splitext(output_path)
            mp3_path = f"{base}.mp3"
            tts.save(mp3_path)
            return True, mp3_path
        except Exception as exc:
            logger.error(f"gTTS fallback failed: {exc}")
            return False, None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        character_name: str,
        text: str,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generate speech with the best available voice.

        Returns the path to the generated audio file, or ``None`` if
        every level failed.
        """
        if filename is None:
            safe_name = re.sub(r"[^a-z0-9_-]", "", character_name.lower().replace(" ", "_"))[:50] or "voice"
            filename = f"{safe_name}_{uuid.uuid4().hex}.wav"
        elif os.sep in filename or "/" in filename or ".." in filename:
            raise ValueError("filename must be a plain file name")

        output_path = os.path.join(self.output_dir, filename)
        if not os.path.realpath(output_path).startswith(os.path.realpath(self.output_dir) + os.sep):
            raise ValueError("output path escapes output_dir")
        temp_dir = os.path.join(self.output_dir, "_temp")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # --- Level 1: FakeYou ---
            model = self._search_model(character_name)
            if model:
                logger.info(
                    f"Found voice model for '{character_name}' on FakeYou: "
                    f"{model['title']}"
                )
                if self._generate_fakeyou(
                    text, model["model_token"], output_path
                ):
                    logger.info(f"Saved audio to {output_path}")
                    return output_path
            else:
                logger.warning(
                    f"'{character_name}' not found on FakeYou."
                )

            # --- Level 2: YouTube + XTTS Clone ---
            # Off by default: cloning a real person's voice needs their consent.
            # Set ALLOW_VOICE_CLONE=1 only for voices you have the right to use.
            ref_audio = None
            if os.getenv("ALLOW_VOICE_CLONE") == "1":
                ref_audio = self._get_youtube_reference_audio(
                    character_name, temp_dir
                )
            if ref_audio and self._generate_xtts_clone(
                text, ref_audio, output_path
            ):
                logger.info(f"Saved XTTS cloned audio to {output_path}")
                return output_path

            # --- Level 3: gTTS Fallback ---
            logger.info("Switching to Level 3 gTTS fallback...")
            ok, final_path = self._generate_fallback(text, output_path)
            if ok and final_path:
                logger.info(f"Saved fallback audio to {final_path}")
                return final_path

            return None
        finally:
            # Always clean up temp files
            shutil.rmtree(temp_dir, ignore_errors=True)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Immersive Voice Agent - Free TTS Module"
    )
    parser.add_argument("character", help="Name of the character")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument(
        "--lang", default="fr", help="Language code (default: fr)"
    )
    args = parser.parse_args()

    generator = VoiceGenerator(language=args.lang)
    result_path = generator.generate(args.character, args.text)

    if result_path:
        print(f"\nSUCCESS: Audio available at {result_path}")
    else:
        print("\nFAILURE: Could not generate audio.")
