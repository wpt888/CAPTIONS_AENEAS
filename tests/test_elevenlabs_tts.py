import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from elevenlabs_tts import (
    ElevenLabsClient,
    alignment_to_words,
    create_caption_segments,
    is_elevenlabs_mp3,
    load_elevenlabs_timing_source,
    safe_file_stem,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class ElevenLabsTTSTests(unittest.TestCase):
    def test_elevenlabs_mp3_is_detected_by_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ElevenLabs_2026-09-19_voice.mp3"
            path.write_bytes(b"fake-mp3")
            self.assertTrue(is_elevenlabs_mp3(path))

    def test_elevenlabs_timing_source_uses_companion_srt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "ElevenLabs_voice.mp3"
            srt_path = audio_path.with_suffix(".srt")
            audio_path.write_bytes(b"fake-mp3")
            srt_path.write_text(
                "1\n00:00:00,120 --> 00:00:00,700\nSalut, lume!\n",
                encoding="utf-8",
            )

            result = load_elevenlabs_timing_source(
                audio_path,
                max_words=2,
                min_duration=0.6,
                max_duration=3.0,
            )

            self.assertIsNotNone(result)
            captions, source = result
            self.assertEqual(Path(source), srt_path)
            self.assertEqual(captions[0]["start"], 0.12)
            self.assertEqual(captions[0]["end"], 0.7)

    def test_elevenlabs_without_timing_source_does_not_fallback_to_whisper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ElevenLabs_voice.mp3"
            path.write_bytes(b"fake-mp3")
            self.assertIsNone(
                load_elevenlabs_timing_source(
                    path,
                    max_words=2,
                    min_duration=0.6,
                    max_duration=3.0,
                )
            )

    def test_alignment_is_converted_to_timed_words(self):
        text = "Salut, lume!"
        alignment = {
            "characters": list(text),
            "character_start_times_seconds": [index * 0.05 for index in range(len(text))],
            "character_end_times_seconds": [(index + 1) * 0.05 for index in range(len(text))],
        }

        words = alignment_to_words(alignment)

        self.assertEqual([word["text"] for word in words], ["Salut,", "lume!"])
        self.assertEqual(words[0]["start"], 0.0)
        self.assertAlmostEqual(words[-1]["end"], len(text) * 0.05)

    def test_segments_keep_provider_clock(self):
        words = [
            {"text": "Un", "start": 0.12, "end": 0.31, "confidence": 1.0},
            {"text": "test", "start": 0.36, "end": 0.70, "confidence": 1.0},
            {"text": "bun.", "start": 0.76, "end": 1.10, "confidence": 1.0},
        ]

        segments = create_caption_segments(words, max_words=2, min_duration=0.2, max_duration=3.0)

        self.assertEqual([segment["text"] for segment in segments], ["Un test", "bun."])
        self.assertEqual(segments[0]["start"], 0.12)
        self.assertEqual(segments[0]["end"], 0.70)
        self.assertEqual(segments[1]["start"], 0.76)

    @patch("elevenlabs_tts.urlopen")
    def test_generate_saves_audio_and_returns_normalized_alignment(self, mocked_urlopen):
        alignment = {
            "characters": ["D", "a"],
            "character_start_times_seconds": [0.0, 0.1],
            "character_end_times_seconds": [0.1, 0.2],
        }
        mocked_urlopen.return_value = FakeResponse({
            "audio_base64": base64.b64encode(b"fake-mp3").decode("ascii"),
            "normalized_alignment": alignment,
        })

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voice.mp3"
            result = ElevenLabsClient("secret").generate_with_timestamps(
                text="Da", voice_id="voice-id", output_path=output_path
            )
            self.assertEqual(output_path.read_bytes(), b"fake-mp3")
            self.assertEqual(result, alignment)

        request = mocked_urlopen.call_args.args[0]
        self.assertIn("/with-timestamps?", request.full_url)
        self.assertNotIn("secret", request.full_url)

    def test_safe_file_stem_removes_diacritics(self):
        self.assertEqual(safe_file_stem("Încearcă această voce acum!"), "incearca_aceasta_voce_acum")


if __name__ == "__main__":
    unittest.main()
