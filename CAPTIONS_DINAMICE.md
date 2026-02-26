# 🚀 Ghid Captions Dinamice

## 🎯 Pentru captions cu puține cuvinte per apariție

### 📱 **Comenzi rapide pentru diferite stiluri:**

#### **TikTok/Instagram (FOARTE dinamic - 1 cuvânt):**
```bash
python dynamic_captions.py "audio.mp3" --words 1 --min-duration 0.5 --max-duration 2.0
```

#### **YouTube Shorts (dinamic - 2 cuvinte):**
```bash
python dynamic_captions.py "audio.mp3" --words 2 --min-duration 0.7 --max-duration 3.0
```

#### **YouTube normal (echilibrat - 3 cuvinte):**
```bash
python dynamic_captions.py "audio.mp3" --words 3 --min-duration 1.0 --max-duration 4.0
```

### ⚙️ **Parametrii principali:**

- `--words X`: Câte cuvinte maxim per caption (1-5 recomandat)
- `--min-duration X`: Cât să dureze minim un caption (secunde)  
- `--max-duration X`: Cât să dureze maxim un caption (secunde)
- `--model tiny/base/medium`: Calitatea transcrierii

### 📊 **Vezi toate preseturile:**
```bash
python dynamic_captions.py --presets
```

### 🎬 **Rezultatele:**
- `audio_dynamic.srt` - Pentru editoare video
- `audio_dynamic.vtt` - Pentru web cu styling
- `audio_dynamic.json` - Date complete
- `audio_dynamic.csv` - Pentru analiză

### 💡 **Tips pentru captions dinamice:**

1. **Pentru TikTok:** Folosește 1-2 cuvinte, foarte rapid
2. **Pentru YouTube:** 2-3 cuvinte este perfect  
3. **Pentru conținut educativ:** 3-4 cuvinte
4. **Model whisper:** `base` e suficient, `medium` pentru precizie maximă

### 🎨 **In editorul video:**
- Importă `.srt` în Premiere/DaVinci
- Setează font bold, mare
- Poziționează jos-centru
- Adaugă outline/shadow pentru contrast

**Perfect pentru look-ul modern de social media!** 🔥