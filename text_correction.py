#!/usr/bin/env python3
"""
Modul pentru corectarea automată a textului transcris folosind textul original
Folosește algoritmi de fuzzy matching și aliniere pentru corectare precisă
"""

import difflib
import re
from typing import List, Dict, Tuple, Optional
import unicodedata


class TextCorrector:
    """Corectează textul transcris folosind textul original ca referință"""

    def __init__(self, original_text: str):
        """
        Inițializează cu textul original

        Args:
            original_text: Textul original folosit în TTS (ElevenLabs)
        """
        self.original_text = self._normalize_text(original_text)
        self.original_words = self._extract_words(self.original_text)
        self.original_sentences = self._extract_sentences(self.original_text)

    def _normalize_text(self, text: str) -> str:
        """Normalizează textul pentru comparare"""
        # Elimină diacriticele pentru comparare mai flexibilă
        # text = ''.join(c for c in unicodedata.normalize('NFD', text)
        #                if unicodedata.category(c) != 'Mn')

        # Păstrează diacriticele dar normalizează spațiile
        text = ' '.join(text.split())
        return text

    def _extract_words(self, text: str) -> List[str]:
        """Extrage cuvintele din text"""
        # Păstrează punctuația atașată la cuvinte
        words = re.findall(r'\S+', text)
        return words

    def _extract_sentences(self, text: str) -> List[str]:
        """Extrage propozițiile din text"""
        # Split pe punctuație de sfârșit de propoziție
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def correct_word(self, word: str, context_words: List[str] = None) -> str:
        """
        Corectează un cuvânt individual

        Args:
            word: Cuvântul de corectat
            context_words: Cuvintele din context pentru matching mai bun

        Returns:
            Cuvântul corectat
        """
        if not word or not word.strip():
            return word

        word_clean = re.sub(r'[^\w\s]', '', word).lower().strip()

        if not word_clean:
            return word

        # Verificare exactă pentru cuvinte scurte comune
        if len(word_clean) <= 2 and word_clean in [w.lower().strip() for w in self.original_words]:
            return word  # Păstrează cuvintele scurte exacte

        # Caută cea mai bună potrivire
        best_match = None
        best_ratio = 0.0

        for orig_word in self.original_words:
            orig_clean = re.sub(r'[^\w\s]', '', orig_word).lower().strip()

            if not orig_clean:
                continue

            # Calculează similaritatea
            ratio = difflib.SequenceMatcher(None, word_clean, orig_clean).ratio()

            # Scad pragul pentru potriviri mai flexible
            if ratio > 0.6 and ratio > best_ratio:
                best_match = orig_word
                best_ratio = ratio

        # Dacă nu găsește potrivire exactă, încearcă căutare parțială
        if not best_match or best_ratio < 0.8:
            for orig_word in self.original_words:
                orig_clean = re.sub(r'[^\w\s]', '', orig_word).lower().strip()

                # Verifică dacă cuvântul transcris este substring în original sau invers
                if len(word_clean) >= 3 and len(orig_clean) >= 3:
                    if word_clean in orig_clean or orig_clean in word_clean:
                        # Preferă cuvintele mai lungi ca fiind mai complete
                        if not best_match or len(orig_word) > len(best_match):
                            best_match = orig_word
                            best_ratio = 0.75

                # Verifică similaritatea fonetică (pentru greșeli de transcripție)
                if len(word_clean) >= 3 and len(orig_clean) >= 3:
                    # Cuvinte care încep la fel
                    if word_clean[:2] == orig_clean[:2]:
                        ratio = difflib.SequenceMatcher(None, word_clean, orig_clean).ratio()
                        if ratio > 0.6 and ratio > best_ratio:
                            best_match = orig_word
                            best_ratio = ratio

        # Dacă găsește o potrivire bună, returnează cuvântul original
        if best_match and best_ratio > 0.5:
            # Păstrează punctuația din cuvântul transcris
            if word and word[-1] in ',.!?;:':
                if best_match[-1] not in ',.!?;:':
                    return best_match + word[-1]
            return best_match

        return word

    def correct_segment(self, segment_text: str, confidence: float = 1.0) -> Tuple[str, bool]:
        """
        Corectează un segment de text

        Args:
            segment_text: Textul segmentului de corectat
            confidence: Nivelul de încredere al transcrierii

        Returns:
            Tuple cu (text corectat, boolean dacă a fost corectat)
        """
        if confidence < 0.5:
            # Pentru transcripții cu încredere scăzută, încearcă matching mai agresiv
            return self._aggressive_correct(segment_text)

        words = segment_text.split()
        corrected_words = []
        was_corrected = False

        for word in words:
            corrected = self.correct_word(word)
            if corrected != word:
                was_corrected = True
            corrected_words.append(corrected)

        return ' '.join(corrected_words), was_corrected

    def _aggressive_correct(self, segment_text: str) -> Tuple[str, bool]:
        """Corectare agresivă pentru text cu încredere scăzută"""
        segment_clean = re.sub(r'[^\w\s]', '', segment_text).lower().strip()

        # Caută cel mai similar fragment din textul original
        best_match = None
        best_ratio = 0.0

        # Creează ferestre glisante din textul original
        original_clean = re.sub(r'[^\w\s]', '', self.original_text).lower()
        words_orig = original_clean.split()
        words_segment = segment_clean.split()

        if not words_segment:
            return segment_text, False

        segment_len = len(words_segment)

        # Încearcă mai multe dimensiuni de ferestre pentru a găsi cea mai bună potrivire
        for window_size in [segment_len, segment_len - 1, segment_len + 1]:
            if window_size <= 0 or window_size > len(words_orig):
                continue

            for i in range(len(words_orig) - window_size + 1):
                window = ' '.join(words_orig[i:i + window_size])
                ratio = difflib.SequenceMatcher(None, segment_clean, window).ratio()

                # Scad pragul pentru o potrivire mai flexibilă
                if ratio > 0.4 and ratio > best_ratio:
                    # Găsește textul original cu punctuație
                    original_words_slice = self.original_words[i:i + window_size]
                    if original_words_slice:
                        best_match = ' '.join(original_words_slice)
                        best_ratio = ratio

        # Dacă nu găsește nimic bun, încearcă cuvânt cu cuvânt
        if not best_match or best_ratio < 0.6:
            corrected_words = []
            for word in words_segment:
                best_word = None
                best_word_ratio = 0.0

                for orig_word in self.original_words:
                    orig_clean = re.sub(r'[^\w\s]', '', orig_word).lower()
                    word_ratio = difflib.SequenceMatcher(None, word, orig_clean).ratio()

                    if word_ratio > 0.6 and word_ratio > best_word_ratio:
                        best_word = orig_word
                        best_word_ratio = word_ratio

                if best_word:
                    corrected_words.append(best_word)
                else:
                    # Încearcă să găsească cuvinte care conțin substring-ul
                    for orig_word in self.original_words:
                        orig_clean = re.sub(r'[^\w\s]', '', orig_word).lower()
                        if word in orig_clean or orig_clean in word:
                            corrected_words.append(orig_word)
                            break
                    else:
                        corrected_words.append(word)  # Păstrează originalul dacă nu găsește nimic

            if corrected_words:
                best_match = ' '.join(corrected_words)
                best_ratio = 0.7  # Consideră că este o corectare validă

        if best_match and best_ratio > 0.3:
            return best_match, True

        return segment_text, False

    def align_and_correct(self, transcribed_words: List[Dict],
                         force_alignment: bool = True) -> List[Dict]:
        """
        Aliniază și corectează cuvintele transcrise cu textul original

        Args:
            transcribed_words: Lista de dicționare cu cuvinte și timestamps
            force_alignment: Dacă să forțeze alinierea cu textul original

        Returns:
            Lista de cuvinte corectate cu timestamps păstrate
        """
        if not force_alignment:
            # Doar corectează cuvintele, păstrează ordinea
            corrected = []
            for word_info in transcribed_words:
                corrected_word = self.correct_word(word_info['text'])
                corrected.append({
                    **word_info,
                    'text': corrected_word,
                    'original_text': word_info['text'],
                    'was_corrected': corrected_word != word_info['text']
                })
            return corrected

        # Aliniere forțată cu textul original
        transcribed_texts = [w['text'] for w in transcribed_words]

        # Curăță textele pentru o comparare mai bună
        transcribed_clean = [re.sub(r'[^\w\s]', '', t).lower().strip() for t in transcribed_texts]
        original_clean = [re.sub(r'[^\w\s]', '', w).lower().strip() for w in self.original_words]

        # Folosește SequenceMatcher pentru aliniere cu texte curățate
        matcher = difflib.SequenceMatcher(None, transcribed_clean, original_clean)

        corrected = []
        orig_idx = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Cuvintele se potrivesc
                for i in range(i1, i2):
                    corrected.append({
                        **transcribed_words[i],
                        'text': self.original_words[j1 + (i - i1)],
                        'original_text': transcribed_words[i]['text'],
                        'was_corrected': False
                    })
            elif tag == 'replace':
                # Înlocuiește cu cuvintele originale
                transcribed_slice = transcribed_words[i1:i2]
                original_slice = self.original_words[j1:j2]

                # Distribuie timestamps-urile
                if transcribed_slice and original_slice:
                    total_duration = transcribed_slice[-1]['end'] - transcribed_slice[0]['start']
                    time_per_word = total_duration / len(original_slice)

                    for idx, orig_word in enumerate(original_slice):
                        start_time = transcribed_slice[0]['start'] + idx * time_per_word
                        end_time = start_time + time_per_word

                        corrected.append({
                            'text': orig_word,
                            'start': start_time,
                            'end': end_time,
                            'confidence': min(w['confidence'] for w in transcribed_slice) if transcribed_slice else 0.5,
                            'original_text': transcribed_slice[min(idx, len(transcribed_slice)-1)]['text'] if transcribed_slice else '',
                            'was_corrected': True
                        })
            elif tag == 'delete':
                # Cuvinte transcrise în plus (zgomot) - le ignorăm
                pass
            elif tag == 'insert':
                # Cuvinte lipsă din transcriere
                # Estimăm timestamps bazat pe context
                if corrected:
                    # Inserăm după ultimul cuvânt
                    prev_word = corrected[-1]
                    time_gap = 0.3  # gap implicit între cuvinte

                    for idx, orig_word in enumerate(self.original_words[j1:j2]):
                        start_time = prev_word['end'] + idx * time_gap
                        end_time = start_time + time_gap

                        corrected.append({
                            'text': orig_word,
                            'start': start_time,
                            'end': end_time,
                            'confidence': 0.5,  # Încredere scăzută pentru cuvinte inserate
                            'original_text': '',
                            'was_corrected': True,
                            'was_inserted': True
                        })

        return corrected


def correct_transcription(transcribed_words: List[Dict],
                         original_text: str,
                         confidence_threshold: float = 0.8) -> List[Dict]:
    """
    Funcție wrapper pentru corectarea transcripției

    Args:
        transcribed_words: Lista de cuvinte transcrise cu timestamps
        original_text: Textul original folosit în TTS
        confidence_threshold: Pragul de încredere pentru corectare agresivă

    Returns:
        Lista de cuvinte corectate
    """
    if not original_text:
        return transcribed_words

    corrector = TextCorrector(original_text)

    # Determină dacă transcripția are încredere scăzută
    avg_confidence = sum(w.get('confidence', 1.0) for w in transcribed_words) / len(transcribed_words) if transcribed_words else 0

    force_alignment = avg_confidence < confidence_threshold

    return corrector.align_and_correct(transcribed_words, force_alignment)


def calculate_correction_stats(corrected_words: List[Dict]) -> Dict:
    """
    Calculează statistici despre corectări

    Args:
        corrected_words: Lista de cuvinte după corectare

    Returns:
        Dicționar cu statistici
    """
    total_words = len(corrected_words)
    corrected_count = sum(1 for w in corrected_words if w.get('was_corrected', False))
    inserted_count = sum(1 for w in corrected_words if w.get('was_inserted', False))

    return {
        'total_words': total_words,
        'corrected_words': corrected_count,
        'inserted_words': inserted_count,
        'correction_rate': (corrected_count / total_words * 100) if total_words > 0 else 0,
        'accuracy_estimate': ((total_words - corrected_count) / total_words * 100) if total_words > 0 else 100
    }