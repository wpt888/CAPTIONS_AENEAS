import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dynamic_captions import DynamicCaptionsGenerator


class DynamicCaptionsTimingTests(unittest.TestCase):
    @patch("dynamic_captions.ElevenLabsClient")
    def test_imported_elevenlabs_mp3_aligns_audio_instead_of_reusing_old_estimate(self, client):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "ElevenLabs_voice.mp3"
            audio_path.write_bytes(b"fake-mp3")
            (audio_path.parent / "ElevenLabs_voice_captions_20260924_100025.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\nSalut lume!\n", encoding="utf-8"
            )
            client.return_value.force_align_audio.return_value = [
                {"text": "Salut", "start": 0.4, "end": 0.7},
                {"text": "lume!", "start": 1.2, "end": 1.6},
            ]

            result = DynamicCaptionsGenerator().generate_dynamic_captions(
                str(audio_path), max_words_per_caption=1, min_duration=0.2,
                original_text="Salut lume!", elevenlabs_api_key="secret"
            )

        client.return_value.force_align_audio.assert_called_once_with(audio_path, "Salut lume!")
        self.assertEqual(result["captions"][0]["start"], 0.4)
        self.assertEqual(result["captions"][0]["end"], 0.7)
        self.assertEqual(result["captions"][1]["start"], 1.2)
        self.assertEqual(result["stats"]["timing_source"], "ElevenLabs forced alignment")

    @patch("dynamic_captions.whisper.transcribe")
    def test_imported_mp3_without_key_uses_audio_transcription(self, transcribe):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "ElevenLabs_voice.mp3"
            audio_path.write_bytes(b"fake-mp3")
            (audio_path.parent / "ElevenLabs_voice_captions_20260924_100025.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\nTimp estimat\n", encoding="utf-8"
            )
            transcribe.return_value = {"segments": [{"words": [
                {"text": "Salut", "start": 0.4, "end": 0.7},
                {"text": "lume!", "start": 1.2, "end": 1.6},
            ]}]}
            generator = DynamicCaptionsGenerator()
            generator.model = object()

            result = generator.generate_dynamic_captions(str(audio_path))

        transcribe.assert_called_once()
        self.assertEqual([caption["text"] for caption in result["captions"]], ["Salut lume!"])
        self.assertEqual(result["captions"][0]["start"], 0.4)


if __name__ == "__main__":
    unittest.main()
