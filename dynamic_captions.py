#!/usr/bin/env python3
"""
Script pentru captions dinamice cu cuvinte puține per apariție
Optimizat pentru look-ul modern de TikTok/YouTube Shorts/Instagram

Autor: AI Assistant pentru workflow ElevenLabs
"""

import os
import json
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

# Setez FFmpeg în PATH dacă există
def setup_ffmpeg_path():
    """Setează FFmpeg în PATH dacă este instalat cu winget"""
    ffmpeg_path = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Microsoft', 'WinGet', 'Packages', 
        'Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe',
        'ffmpeg-8.0-full_build', 'bin'
    )
    
    if os.path.exists(ffmpeg_path):
        current_path = os.environ.get('PATH', '')
        if ffmpeg_path not in current_path:
            os.environ['PATH'] = current_path + os.pathsep + ffmpeg_path
            print(f"FFmpeg adaugat la PATH: {ffmpeg_path}")
        return True
    return False

# Configurez FFmpeg înainte de import-uri
setup_ffmpeg_path()

try:
    import whisper_timestamped as whisper
    from pydub import AudioSegment
    from text_correction import correct_transcription, calculate_correction_stats, TextCorrector
except ImportError as e:
    print(f"❌ Eroare la importul bibliotecilor: {e}")
    print("Rulează Start_CaptionsUI.bat pentru configurarea automată a mediului.")
    if 'text_correction' in str(e):
        print("❗ Modulul text_correction.py lipsește din director")
    raise SystemExit(1)


class DynamicCaptionsGenerator:
    """Generator pentru captions dinamice cu segmente scurte"""

    # Extensii video suportate pentru extragere audio
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    # Extensii audio suportate direct
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self._temp_audio_file = None  # Pentru cleanup

    def _is_video_file(self, file_path: Path) -> bool:
        """Verifică dacă fișierul este video"""
        return file_path.suffix.lower() in self.VIDEO_EXTENSIONS

    def _is_audio_file(self, file_path: Path) -> bool:
        """Verifică dacă fișierul este audio"""
        return file_path.suffix.lower() in self.AUDIO_EXTENSIONS

    def _extract_audio_from_video(self, video_path: Path) -> Optional[Path]:
        """
        Extrage coloana sonoră din fișierul video folosind FFmpeg

        Args:
            video_path: Calea către fișierul video

        Returns:
            Calea către fișierul audio temporar sau None dacă extragerea eșuează
        """
        try:
            # Creează un fișier temporar pentru audio
            # Sanitizează numele pentru a evita probleme cu caractere speciale
            import hashlib
            safe_name = hashlib.md5(video_path.name.encode()).hexdigest()[:12]
            temp_dir = tempfile.gettempdir()
            temp_audio_path = Path(temp_dir) / f"caption_audio_{safe_name}.wav"

            print(f"🎬 Extrag coloana sonoră din: {video_path.name}")

            # Comandă FFmpeg pentru extragere audio
            # -y: suprascrie fișierul dacă există
            # -i: input file
            # -vn: dezactivează video (extrage doar audio)
            # -acodec pcm_s16le: codec audio WAV standard
            # -ar 16000: sample rate 16kHz (optim pentru Whisper)
            # -ac 1: mono (suficient pentru speech recognition)
            cmd = [
                'ffmpeg',
                '-y',
                '-i', str(video_path),
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                str(temp_audio_path)
            ]

            # Rulează FFmpeg cu encoding explicit pentru Windows
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                encoding='utf-8',
                errors='replace'  # Înlocuiește caracterele invalide
            )

            if result.returncode != 0:
                print(f"⚠️ Prima încercare FFmpeg a eșuat, încerc varianta simplificată...")
                # Încearcă o variantă simplificată - lasă FFmpeg să aleagă codec-ul
                cmd_simple = [
                    'ffmpeg',
                    '-y',
                    '-i', str(video_path),
                    '-vn',
                    '-acodec', 'pcm_s16le',  # WAV standard
                    str(temp_audio_path)
                ]
                result = subprocess.run(
                    cmd_simple,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    encoding='utf-8',
                    errors='replace'
                )

                if result.returncode != 0:
                    # Ultima încercare - extrage audio fără nicio specificație
                    cmd_last = [
                        'ffmpeg',
                        '-y',
                        '-i', str(video_path),
                        '-vn',
                        str(temp_audio_path)
                    ]
                    result = subprocess.run(
                        cmd_last,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        encoding='utf-8',
                        errors='replace'
                    )

                    if result.returncode != 0:
                        print(f"❌ Nu pot extrage audio din video: {result.stderr[:200] if result.stderr else 'Eroare necunoscută'}")
                        return None

            if temp_audio_path.exists():
                print(f"✅ Audio extras: {temp_audio_path.name}")
                self._temp_audio_file = temp_audio_path  # Salvează pentru cleanup
                return temp_audio_path
            else:
                print("❌ Fișierul audio nu a fost creat")
                return None

        except subprocess.TimeoutExpired:
            print("❌ Timeout la extragerea audio (> 5 minute)")
            # Curăță fișierul parțial creat dacă există
            if temp_audio_path.exists():
                try:
                    temp_audio_path.unlink()
                except:
                    pass
            return None
        except FileNotFoundError:
            print("❌ FFmpeg nu este instalat sau nu este în PATH!")
            print("   Instalează FFmpeg: winget install Gyan.FFmpeg")
            return None
        except Exception as e:
            print(f"❌ Eroare la extragerea audio: {e}")
            # Curăță fișierul parțial creat dacă există
            if 'temp_audio_path' in locals() and temp_audio_path.exists():
                try:
                    temp_audio_path.unlink()
                except:
                    pass
            return None

    def _cleanup_temp_audio(self):
        """Șterge fișierul audio temporar dacă există"""
        if self._temp_audio_file and self._temp_audio_file.exists():
            try:
                self._temp_audio_file.unlink()
                print(f"🧹 Fișier temporar șters: {self._temp_audio_file.name}")
            except Exception as e:
                print(f"⚠️ Nu pot șterge fișierul temporar: {e}")
            finally:
                self._temp_audio_file = None
    
    def _clean_text(self, text: str, remove_punctuation: bool = False, text_case: str = "normal") -> str:
        """
        Curăță textul conform opțiunilor de formatare
        
        Args:
            text: Textul de curățat
            remove_punctuation: Elimină semnele de punctuație
            text_case: Formatarea ("normal", "upper", "lower")
        """
        cleaned_text = text.strip()
        
        # Elimină semnele de punctuație dacă este cerut
        if remove_punctuation:
            import string
            # Păstrează spațiile și literele, elimină punctuația
            cleaned_text = ''.join(char for char in cleaned_text 
                                 if char not in string.punctuation or char == ' ')
            # Curăță spațiile multiple
            cleaned_text = ' '.join(cleaned_text.split())
        
        # Formatează textul conform opțiunii
        if text_case == "upper":
            cleaned_text = cleaned_text.upper()
        elif text_case == "lower":
            cleaned_text = cleaned_text.lower()
        # "normal" rămâne neschimbat
        
        return cleaned_text
        
    def load_model(self):
        """Încarcă modelul Whisper"""
        if not self.model:
            print(f"Incarcare model Whisper: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            print("Model incarcat!")
    
    def generate_dynamic_captions(self, audio_path: str,
                                max_words_per_caption: int = 2,
                                min_duration: float = 0.6,
                                max_duration: float = 2.5,
                                output_dir: str = None,
                                remove_punctuation: bool = False,
                                text_case: str = "normal",
                                original_text: str = None) -> Dict[str, Any]:
        """
        Generează captions dinamice cu controale fine

        Args:
            audio_path: Calea către fișierul audio SAU video (MP4, AVI, MKV, etc.)
            max_words_per_caption: Numărul maxim de cuvinte per caption
            min_duration: Durata minimă a unui caption (secunde)
            max_duration: Durata maximă a unui caption (secunde)
            output_dir: Directorul de output
            remove_punctuation: Elimină semnele de punctuație
            text_case: Formatarea textului ("normal", "upper", "lower")
            original_text: Textul original pentru corectare automată
        """

        if not self.model:
            self.load_model()

        input_path = Path(audio_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Fișierul nu există: {input_path}")

        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Detectează tipul fișierului și extrage audio dacă e video
        processing_path = input_path
        is_video = self._is_video_file(input_path)

        if is_video:
            print(f"🎬 Fișier video detectat: {input_path.name}")
            extracted_audio = self._extract_audio_from_video(input_path)
            if extracted_audio is None:
                raise RuntimeError(f"Nu pot extrage audio din: {input_path.name}. Verifică dacă FFmpeg este instalat.")
            processing_path = extracted_audio
        elif not self._is_audio_file(input_path):
            # Încearcă oricum (Whisper poate procesa multe formate)
            print(f"⚠️ Format necunoscut: {input_path.suffix}, încerc procesarea directă...")

        try:
            print(f"🎵 Procesare audio pentru captions dinamice: {input_path.name}")
            print(f"⚙️ Setări: max {max_words_per_caption} cuvinte/caption, durată {min_duration}-{max_duration}s")

            # Transcrie cu timestamps per cuvânt
            result = whisper.transcribe(
                self.model,
                str(processing_path),
                language="ro"
            )

            # Extrage cuvintele cu timestamps precise
            all_words = []
            for segment in result.get('segments', []):
                # Dacă nu avem word-level timestamps, creăm din segment
                if 'words' in segment and segment['words']:
                    for word_info in segment.get('words', []):
                        word_data = {
                            'text': word_info.get('text', '').strip(),
                            'start': float(word_info.get('start', 0)),
                            'end': float(word_info.get('end', 0)),
                            'confidence': word_info.get('confidence', 1.0)
                        }
                        if word_data['text']:  # Ignoră cuvintele goale
                            # Aplică formatarea textului
                            word_data['text'] = self._clean_text(word_data['text'], remove_punctuation, text_case)
                            if word_data['text']:  # Verifică din nou după curățare
                                all_words.append(word_data)
                else:
                    # Fallback: împarte textul segmentului în cuvinte și distribuie timpul
                    text = segment.get('text', '').strip()
                    if text:
                        words_in_segment = text.split()
                        segment_start = segment.get('start', 0)
                        segment_end = segment.get('end', 0)
                        segment_duration = segment_end - segment_start

                        if words_in_segment:
                            word_duration = segment_duration / len(words_in_segment)

                            for i, word in enumerate(words_in_segment):
                                word_start = segment_start + (i * word_duration)
                                word_end = word_start + word_duration

                                word_data = {
                                    'text': self._clean_text(word.strip(), remove_punctuation, text_case),
                                    'start': word_start,
                                    'end': word_end,
                                    'confidence': segment.get('avg_logprob', 1.0)
                                }
                                if word_data['text']:  # Verifică după curățare
                                    all_words.append(word_data)

            print(f"Găsite {len(all_words)} cuvinte cu timestamps")

            # Aplică corectarea dacă avem text original
            correction_stats = None
            if original_text and all_words:
                print("Aplic corectarea avansată folosind textul original...")
                all_words_before = all_words.copy()

                # Folosește algoritmul avansat pentru corectare perfectă
                all_words = correct_transcription(all_words, original_text)

                # Calculează statistici de corectare
                correction_stats = calculate_correction_stats(all_words)
                print(f"Corectare avansată completă: {correction_stats['corrected_words']} cuvinte corectate ({correction_stats['correction_rate']:.1f}%)")
                print(f"Cuvinte inserate: {correction_stats['inserted_words']}")
                print(f"Acuratețe estimată: {correction_stats['accuracy_estimate']:.1f}%")

            # Creează caption-uri dinamice cu timing simplu și precis
            dynamic_captions = self._create_simple_segments(
                all_words,
                max_words_per_caption,
                min_duration,
                max_duration,
                remove_punctuation,
                text_case
            )

            # Nu mai salvez automat - UI-ul controlează ce formate să salveze

            print(f"✅ Captions dinamice generate!")
            print(f"📊 {len(dynamic_captions)} caption-uri create din {len(all_words)} cuvinte")
            print(f"💾 Gata pentru salvare în formatele selectate...")

            stats = {
                'total_words': len(all_words),
                'total_captions': len(dynamic_captions),
                'avg_words_per_caption': len(all_words) / len(dynamic_captions) if dynamic_captions else 0,
                'total_duration': dynamic_captions[-1]['end'] if dynamic_captions else 0,
                'source_was_video': is_video
            }

            # Adaugă statisticile de corectare dacă există
            if correction_stats:
                stats['correction_applied'] = True
                stats['corrected_words'] = correction_stats['corrected_words']
                stats['correction_rate'] = correction_stats['correction_rate']
                stats['accuracy_estimate'] = correction_stats['accuracy_estimate']

            return {
                'captions': dynamic_captions,
                'stats': stats
            }

        finally:
            # Curăță fișierul audio temporar dacă a fost extras din video
            if is_video:
                self._cleanup_temp_audio()
    
    def _create_simple_segments(self, words: List[Dict],
                               max_words: int,
                               min_duration: float,
                               max_duration: float,
                               remove_punctuation: bool = False,
                               text_case: str = "normal") -> List[Dict[str, Any]]:
        """Creează segmente simple cu timing precis fără suprapuneri"""

        if not words:
            return []

        segments = []
        current_words = []
        last_end_time = 0  # Track pentru a evita suprapunerile

        i = 0
        while i < len(words):
            current_words.append(words[i])

            # Condițiile simple pentru închiderea segmentului
            should_close = False

            # 1. PRIORITATE MAXIMĂ: Punctuație de sfârșit de propoziție
            # Închide imediat dacă cuvântul curent se termină cu ., !, ?
            current_text = words[i]['text'].strip()
            if current_text.endswith(('.', '!', '?')):
                should_close = True

            # 2. Am atins numărul maxim de cuvinte (doar dacă nu avem punctuație)
            elif len(current_words) >= max_words:
                should_close = True

            # 3. Pauză mare între cuvinte (peste 0.5s = oprire naturală)
            elif i + 1 < len(words):
                gap = words[i + 1]['start'] - words[i]['end']
                if gap > 0.5:
                    should_close = True

            # 4. Sfârșitul listei de cuvinte
            elif i == len(words) - 1:
                should_close = True

            if should_close and current_words:
                # Timing STRICT pentru a evita suprapunerile
                segment_start = max(current_words[0]['start'], last_end_time + 0.05)  # 50ms gap minim
                segment_end = current_words[-1]['end']

                # Asigură durata minimă fără să creeze suprapuneri
                natural_duration = segment_end - segment_start
                if natural_duration < min_duration:
                    # Extinde sfârșitul, dar verifică conflictele
                    desired_end = segment_start + min_duration

                    # Verifică dacă avem conflict cu următorul segment
                    if i + 1 < len(words):
                        next_start = words[i + 1]['start']
                        # Limitează extensia pentru a nu crea suprapuneri
                        segment_end = min(desired_end, next_start - 0.05)
                    else:
                        # Ultimul segment, poate fi extins liber
                        segment_end = desired_end

                # Asigură că nu există suprapunere cu segmentul anterior
                if segment_start < last_end_time + 0.05:
                    segment_start = last_end_time + 0.05

                # Verificare finală: durata minimă realistică
                final_duration = segment_end - segment_start
                if final_duration < 0.2:  # Minim 200ms pentru lizibilitate
                    segment_end = segment_start + 0.2

                # Aplică formatarea textului în segmentul final
                words_text = [word['text'] for word in current_words]
                segment_text = ' '.join(words_text)
                segment_text = self._clean_text(segment_text, remove_punctuation, text_case)

                segments.append({
                    'id': len(segments) + 1,
                    'text': segment_text,
                    'start': segment_start,
                    'end': segment_end,
                    'word_count': len(current_words),
                    'words': current_words.copy(),
                    'duration': segment_end - segment_start
                })

                # Actualizează timpul de sfârșit pentru următorul segment
                last_end_time = segment_end
                current_words = []

            i += 1

        return segments
    
    def _save_dynamic_srt(self, segments: List[Dict], output_path: Path):
        """Salvează în format SRT optimizat pentru captions dinamice"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                start_time = self._format_time_srt(segment['start'])
                end_time = self._format_time_srt(segment['end'])
                
                f.write(f"{segment['id']}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
    
    def _save_dynamic_vtt(self, segments: List[Dict], output_path: Path):
        """Salvează în format VTT cu styling pentru captions dinamice"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n")
            f.write("Kind: captions\n")
            f.write("Language: ro\n\n")
            
            # Adaugă stiluri pentru captions dinamice
            f.write("STYLE\n")
            f.write("::cue {\n")
            f.write("  background-color: rgba(0, 0, 0, 0.8);\n")
            f.write("  color: white;\n")
            f.write("  font-size: 120%;\n")
            f.write("  font-weight: bold;\n")
            f.write("  text-align: center;\n")
            f.write("  line-height: 1.2;\n")
            f.write("}\n\n")
            
            for segment in segments:
                start_time = self._format_time_vtt(segment['start'])
                end_time = self._format_time_vtt(segment['end'])
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
    
    def _save_dynamic_json(self, segments: List[Dict], output_path: Path, metadata: Dict):
        """Salvează în format JSON cu metadata completă"""
        data = {
            'metadata': {
                'generator': 'DynamicCaptionsGenerator',
                'settings': metadata,
                'generated_at': str(Path(__file__).stat().st_mtime)
            },
            'segments': segments
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_dynamic_csv(self, segments: List[Dict], output_path: Path):
        """Salvează în format CSV pentru analiză"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("id,start,end,duration,word_count,text\n")
            for segment in segments:
                text_escaped = segment['text'].replace('"', '""')
                f.write(f'{segment["id"]},{segment["start"]:.3f},{segment["end"]:.3f},'
                       f'{segment["duration"]:.3f},{segment["word_count"]},"{text_escaped}"\n')
    
    def _format_time_srt(self, seconds: float) -> str:
        """Formatează timpul pentru SRT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_time_vtt(self, seconds: float) -> str:
        """Formatează timpul pentru VTT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    # Metode publice pentru UI
    def save_srt(self, segments: List[Dict], output_path: str):
        """Metodă publică pentru salvare SRT"""
        self._save_dynamic_srt(segments, Path(output_path))
    
    def save_vtt(self, segments: List[Dict], output_path: str):
        """Metodă publică pentru salvare VTT"""
        self._save_dynamic_vtt(segments, Path(output_path))
    
    def save_json(self, segments: List[Dict], output_path: str):
        """Metodă publică pentru salvare JSON"""
        metadata = {
            'generator': 'DynamicCaptionsGenerator',
            'timestamp': str(Path(__file__).stat().st_mtime)
        }
        self._save_dynamic_json(segments, Path(output_path), metadata)
    
    def save_csv(self, segments: List[Dict], output_path: str):
        """Metodă publică pentru salvare CSV"""
        self._save_dynamic_csv(segments, Path(output_path))


def main():
    """Funcția principală pentru captions dinamice"""
    parser = argparse.ArgumentParser(
        description="Generator captions dinamice pentru video modern (suportă audio și video)"
    )

    parser.add_argument("media_file", nargs='?',
                       help="Calea către fișierul audio (MP3, WAV, etc.) sau video (MP4, AVI, MKV, etc.)")
    parser.add_argument("--words", type=int, default=2,
                       help="Numărul maxim de cuvinte per caption (1-10, default: 2)")
    parser.add_argument("--min-duration", type=float, default=0.6,
                       help="Durata minimă per caption în secunde (default: 0.6)")
    parser.add_argument("--max-duration", type=float, default=2.5,
                       help="Durata maximă per caption în secunde (default: 2.5)")
    parser.add_argument("--model", default="base", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Modelul Whisper (default: base)")
    parser.add_argument("--output-dir", help="Directorul de output")
    parser.add_argument("--no-punctuation", action="store_true",
                       help="Elimină semnele de punctuație din captions")
    parser.add_argument("--text-case", choices=["normal", "upper", "lower"], default="normal",
                       help="Formatarea textului (default: normal)")
    parser.add_argument("--presets", action="store_true", 
                       help="Arată preseturile pentru diferite tipuri de video")
    
    args = parser.parse_args()
    
    if args.presets:
        print("""
🎬 PRESETURI PENTRU CAPTIONS DINAMICE

📱 TikTok/Instagram Stories (foarte dinamic):
   --words 1 --min-duration 0.5 --max-duration 2.0

📺 YouTube Shorts (dinamic):
   --words 2 --min-duration 0.7 --max-duration 3.0

🎥 YouTube regulat (echilibrat):
   --words 3 --min-duration 1.0 --max-duration 4.0

📚 Tutorial/Educational (mai lung):
   --words 4 --min-duration 1.5 --max-duration 6.0

🎤 Podcast (relaxat):
   --words 5 --min-duration 2.0 --max-duration 8.0

🎵 FORMATE SUPORTATE:
   Audio: MP3, WAV, M4A, FLAC, OGG, AAC, WMA
   Video: MP4, AVI, MKV, MOV, WMV, FLV, WEBM, M4V
   (Audio-ul este extras automat din fișierele video)

Exemple:
  # Pentru TikTok foarte dinamic (cu audio)
  python dynamic_captions.py audio.mp3 --words 1 --min-duration 0.5 --max-duration 2.0

  # Pentru YouTube Shorts (cu video MP4)
  python dynamic_captions.py video.mp4 --words 2 --min-duration 0.7 --max-duration 3.0
        """)
        return
    
    if not args.media_file:
        print("❌ Lipsește fișierul media. Folosește --presets pentru a vedea exemplele.")
        return 1

    if args.words < 1 or args.words > 10:
        print("❌ Numărul de cuvinte trebuie să fie între 1 și 10")
        return 1

    if args.min_duration > args.max_duration:
        print("❌ Durata minimă nu poate fi mai mare decât cea maximă")
        return 1

    # Detectează tipul fișierului
    media_ext = Path(args.media_file).suffix.lower()
    is_video = media_ext in DynamicCaptionsGenerator.VIDEO_EXTENSIONS
    file_type = "🎬 Video" if is_video else "🎵 Audio"

    print("🎬 Generator Captions Dinamice")
    print("=" * 50)
    print(f"{file_type}: {args.media_file}")
    print(f"📊 Setări: {args.words} cuvinte max, {args.min_duration}-{args.max_duration}s")
    if args.no_punctuation:
        print("✂️  Eliminare punctuație: DA")
    if args.text_case != "normal":
        print(f"🔤 Formatare text: {args.text_case.upper()}")

    try:
        generator = DynamicCaptionsGenerator(args.model)
        result = generator.generate_dynamic_captions(
            args.media_file,
            max_words_per_caption=args.words,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            output_dir=args.output_dir,
            remove_punctuation=args.no_punctuation,
            text_case=args.text_case
        )

        stats = result['stats']
        print(f"\n📈 STATISTICI:")
        print(f"   • {stats['total_captions']} caption-uri create")
        print(f"   • {stats['total_words']} cuvinte procesate")
        print(f"   • {stats['avg_words_per_caption']:.1f} cuvinte/caption în medie")
        print(f"   • {stats['total_duration']:.1f}s durată totală")
        if stats.get('source_was_video'):
            print(f"   • Sursă: Video (audio extras automat)")

        print(f"\n🎉 Success! Captions dinamice generate cu succes!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
