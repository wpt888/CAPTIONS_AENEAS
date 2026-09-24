"""Client ElevenLabs minimal pentru generare MP3 + captions sincronizate."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ElevenLabsError(RuntimeError):
    """Eroare sigură, potrivită pentru afișare în interfață."""


def is_elevenlabs_mp3(audio_path: str | Path) -> bool:
    """Identifică un MP3 ElevenLabs fără să decodeze audio-ul.

    MP3-urile descărcate din ElevenLabs folosesc de obicei prefixul
    ``ElevenLabs_`` și includ markerul C2PA ``ElevenLabs`` în ID3. Sunt
    acceptate ambele semnale, deoarece fișierele mai vechi pot să nu aibă
    manifestul C2PA.
    """
    path = Path(audio_path)
    if path.suffix.lower() != ".mp3":
        return False
    if path.name.casefold().startswith("elevenlabs_"):
        return True

    try:
        with path.open("rb") as audio_file:
            header = audio_file.read(1024 * 1024)
    except OSError:
        return False

    header_lower = header.lower()
    return b"elevenlabs" in header_lower and b"c2pa" in header_lower


def _format_provider_text(text: str, remove_punctuation: bool, text_case: str) -> str:
    return _format_text(text, remove_punctuation, text_case).strip()


def _normalize_segments(
    segments: Iterable[dict[str, Any]],
    *,
    remove_punctuation: bool,
    text_case: str,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for segment in segments:
        try:
            start = float(segment["start"])
            end = float(segment["end"])
        except (KeyError, TypeError, ValueError):
            continue
        text = _format_provider_text(
            str(segment.get("text", "")), remove_punctuation, text_case
        )
        if not text or end <= start:
            continue
        normalized.append({
            "id": len(normalized) + 1,
            "text": text,
            "start": start,
            "end": end,
            "word_count": len(text.split()),
            "words": [dict(word) for word in segment.get("words", [])],
            "duration": end - start,
        })
    return normalized


def _parse_srt_time(value: str) -> float:
    value = value.strip().replace(",", ".")
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _read_srt_segments(
    path: Path,
    *,
    remove_punctuation: bool,
    text_case: str,
) -> list[dict[str, Any]]:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")

    parsed: list[dict[str, Any]] = []
    blocks = re.split(r"\r?\n\s*\r?\n", content.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next(
            (index for index, line in enumerate(lines) if "-->" in line), None
        )
        if timing_index is None or timing_index + 1 >= len(lines):
            continue
        start_text, end_text = [part.strip() for part in lines[timing_index].split("-->", 1)]
        try:
            start = _parse_srt_time(start_text.split()[0])
            end = _parse_srt_time(end_text.split()[0])
        except (ValueError, IndexError):
            continue
        parsed.append({"start": start, "end": end, "text": " ".join(lines[timing_index + 1:])})
    return _normalize_segments(
        parsed,
        remove_punctuation=remove_punctuation,
        text_case=text_case,
    )


def _read_json_timing_source(
    path: Path,
    *,
    max_words: int,
    min_duration: float,
    max_duration: float,
    remove_punctuation: bool,
    text_case: str,
) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as metadata_file:
        payload = json.load(metadata_file)

    if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
        return _normalize_segments(
            payload["segments"],
            remove_punctuation=remove_punctuation,
            text_case=text_case,
        )

    alignment = payload.get("alignment") if isinstance(payload, dict) else None
    if not alignment and isinstance(payload, dict):
        alignment = payload.get("normalized_alignment")
    if isinstance(alignment, dict):
        words = alignment_to_words(alignment)
        return create_caption_segments(
            words,
            max_words=max_words,
            min_duration=min_duration,
            max_duration=max_duration,
            remove_punctuation=remove_punctuation,
            text_case=text_case,
        )
    return []


def load_elevenlabs_timing_source(
    audio_path: str | Path,
    *,
    max_words: int,
    min_duration: float,
    max_duration: float,
    remove_punctuation: bool = False,
    text_case: str = "normal",
) -> tuple[list[dict[str, Any]], str] | None:
    """Încarcă timingurile ElevenLabs asociate unui MP3.

    API-ul ElevenLabs livrează alinierea în răspunsul JSON, nu în fluxul audio
    MP3. Fluxul local păstrează acea aliniere în SRT/JSON lângă MP3; funcția
    caută mai întâi aceste surse și nu pornește Whisper dacă le găsește.
    """
    path = Path(audio_path)
    if not is_elevenlabs_mp3(path):
        return None

    # Exporturile _captions_* pot proveni din vechea estimare pe durata totală.
    # Nu le reutilizăm ca și cum ar avea timpi măsurați din audio.
    json_candidates = [path.with_suffix(".elevenlabs.json"), path.with_suffix(".json")]
    for candidate in json_candidates:
        if not candidate.is_file():
            continue
        try:
            captions = _read_json_timing_source(
                candidate,
                max_words=max_words,
                min_duration=min_duration,
                max_duration=max_duration,
                remove_punctuation=remove_punctuation,
                text_case=text_case,
            )
        except (OSError, ValueError, KeyError, TypeError, ElevenLabsError):
            continue
        if captions:
            return captions, str(candidate)

    srt_candidates = [path.with_suffix(".srt")]
    srt_candidates.extend(sorted(path.parent.glob(f"{path.stem}_approved_*.srt"), reverse=True))
    for candidate in srt_candidates:
        if not candidate.is_file():
            continue
        try:
            captions = _read_srt_segments(
                candidate,
                remove_punctuation=remove_punctuation,
                text_case=text_case,
            )
        except OSError:
            continue
        if captions:
            return captions, str(candidate)
    return None


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

    def force_align_audio(self, audio_path: str | Path, text: str) -> list[dict[str, Any]]:
        """Obține timpii cuvintelor din MP3-ul existent și transcriptul său."""
        path = Path(audio_path)
        if not text.strip():
            raise ElevenLabsError("Introdu textul original pentru alinierea audio.")
        try:
            audio_bytes = path.read_bytes()
        except OSError as error:
            raise ElevenLabsError(f"Nu pot citi fișierul audio: {path}") from error

        boundary = f"codex-{uuid.uuid4().hex}"
        filename = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n".encode()
            + text.encode("utf-8")
            + f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode("utf-8")
            + audio_bytes
            + f"\r\n--{boundary}--\r\n".encode()
        )
        request = Request(
            f"{self.BASE_URL}/forced-alignment",
            data=body,
            method="POST",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        payload = self._request_json(request)
        words = payload.get("words") if isinstance(payload, dict) else None
        if not isinstance(words, list) or not words:
            raise ElevenLabsError("ElevenLabs nu a returnat timpi pe cuvinte.")
        timed_words = []
        for word in words:
            try:
                word_text = str(word["text"]).strip()
                start, end = float(word["start"]), float(word["end"])
            except (KeyError, TypeError, ValueError) as error:
                raise ElevenLabsError("Răspunsul de aliniere ElevenLabs este incomplet.") from error
            if not word_text:
                continue
            if start < 0 or end <= start:
                raise ElevenLabsError("ElevenLabs a returnat timpi invalizi pentru un cuvânt.")
            timed_words.append({"text": word_text, "start": start, "end": end, "confidence": 1.0})
        if not timed_words:
            raise ElevenLabsError("ElevenLabs nu a returnat cuvinte temporizate.")
        return timed_words

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
