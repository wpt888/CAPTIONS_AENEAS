"""Client ElevenLabs minimal pentru generare MP3 + captions sincronizate."""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ElevenLabsError(RuntimeError):
    """Eroare sigură, potrivită pentru afișare în interfață."""


class ElevenLabsClient:
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str, timeout: int = 180):
        api_key = api_key.strip()
        if not api_key:
            raise ElevenLabsError("Introdu cheia API ElevenLabs.")
        self.api_key = api_key
        self.timeout = timeout

    def _request_json(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            message = f"ElevenLabs a răspuns cu HTTP {error.code}."
            try:
                payload = json.loads(error.read().decode("utf-8"))
                detail = payload.get("detail")
                if isinstance(detail, dict):
                    detail = detail.get("message") or detail.get("status")
                if detail:
                    message = f"{message} {detail}"
            except (ValueError, UnicodeDecodeError):
                pass
            raise ElevenLabsError(message) from error
        except URLError as error:
            raise ElevenLabsError(
                "Nu mă pot conecta la ElevenLabs. Verifică internetul."
            ) from error
        except json.JSONDecodeError as error:
            raise ElevenLabsError("Răspuns ElevenLabs invalid.") from error

    def list_voices(self) -> list[dict[str, str]]:
        request = Request(
            f"{self.BASE_URL}/voices",
            headers={"xi-api-key": self.api_key, "Accept": "application/json"},
        )
        payload = self._request_json(request)
        voices = [
            {"id": str(voice.get("voice_id", "")), "name": str(voice.get("name", "Voce"))}
            for voice in payload.get("voices", [])
            if voice.get("voice_id")
        ]
        return sorted(voices, key=lambda voice: voice["name"].casefold())

    def generate_with_timestamps(
        self,
        *,
        text: str,
        voice_id: str,
        output_path: Path,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.57,
        similarity_boost: float = 0.75,
        style: float = 0.22,
        speed: float = 1.0,
        use_speaker_boost: bool = True,
    ) -> dict[str, Any]:
        if not text.strip():
            raise ElevenLabsError("Textul pentru voce este gol.")
        if not voice_id.strip():
            raise ElevenLabsError("Selectează o voce ElevenLabs.")

        query = urlencode({"output_format": "mp3_44100_128"})
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/with-timestamps?{query}"
        body = {
            "text": text,
            "model_id": model_id,
            "language_code": "ro",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "speed": speed,
                "use_speaker_boost": use_speaker_boost,
            },
        }
        request = Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        payload = self._request_json(request)

        audio_b64 = payload.get("audio_base64")
        alignment = payload.get("normalized_alignment") or payload.get("alignment")
        if not audio_b64 or not alignment:
            raise ElevenLabsError("Răspunsul nu conține audio și timestampuri.")

        try:
            audio_bytes = base64.b64decode(audio_b64, validate=True)
        except (ValueError, TypeError) as error:
            raise ElevenLabsError("Audio ElevenLabs invalid.") from error

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return alignment


def alignment_to_words(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    """Transformă alignment-ul pe caractere ElevenLabs în cuvinte temporizate."""
    characters = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if not characters or not (len(characters) == len(starts) == len(ends)):
        raise ElevenLabsError("Timestampurile ElevenLabs sunt incomplete.")

    words: list[dict[str, Any]] = []
    current: list[str] = []
    word_start: float | None = None
    word_end = 0.0

    def flush() -> None:
        nonlocal current, word_start, word_end
        text = "".join(current).strip()
        if text and word_start is not None:
            words.append({
                "text": text,
                "start": float(word_start),
                "end": max(float(word_end), float(word_start) + 0.01),
                "confidence": 1.0,
            })
        current = []
        word_start = None
        word_end = 0.0

    for character, start, end in zip(characters, starts, ends):
        character = str(character)
        if character.isspace():
            flush()
            continue
        if word_start is None:
            word_start = float(start)
        current.append(character)
        word_end = float(end)
    flush()
    return words


def _format_text(text: str, remove_punctuation: bool, text_case: str) -> str:
    if remove_punctuation:
        text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    if text_case == "upper":
        return text.upper()
    if text_case == "lower":
        return text.lower()
    return text


def create_caption_segments(
    words: list[dict[str, Any]],
    *,
    max_words: int = 2,
    min_duration: float = 0.6,
    max_duration: float = 3.0,
    remove_punctuation: bool = False,
    text_case: str = "normal",
) -> list[dict[str, Any]]:
    """Grupează cuvintele fără a pierde ceasul exact primit de la provider."""
    if not words:
        return []

    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    for index, word in enumerate(words):
        current.append(word)
        next_word = words[index + 1] if index + 1 < len(words) else None
        duration = float(current[-1]["end"]) - float(current[0]["start"])
        closes_sentence = str(word["text"]).rstrip().endswith((".", "!", "?"))
        large_gap = bool(next_word and float(next_word["start"]) - float(word["end"]) > 0.5)
        should_close = (
            closes_sentence
            or len(current) >= max(1, int(max_words))
            or duration >= max_duration
            or large_gap
            or next_word is None
        )
        if not should_close:
            continue

        start = float(current[0]["start"])
        end = float(current[-1]["end"])
        if end - start < min_duration:
            desired_end = start + min_duration
            end = min(desired_end, float(next_word["start"])) if next_word else desired_end
        end = max(end, start + 0.01)
        text = _format_text(
            " ".join(str(item["text"]) for item in current),
            remove_punctuation,
            text_case,
        ).strip()
        if text:
            segments.append({
                "id": len(segments) + 1,
                "text": text,
                "start": start,
                "end": end,
                "word_count": len(current),
                "words": [dict(item) for item in current],
                "duration": end - start,
            })
        current = []

    return segments


def safe_file_stem(text: str, fallback: str = "elevenlabs") -> str:
    """Creează un nume de fișier scurt și portabil din începutul textului."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[A-Za-z0-9]+", ascii_text)[:6]
    return ("_".join(words).lower()[:80].rstrip("_") or fallback)
