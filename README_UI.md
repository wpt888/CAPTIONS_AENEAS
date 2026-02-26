# 🎬 Dynamic Captions Generator - UI Grafic

Sistem complet pentru generarea de captions dinamice din fișiere audio, cu interfață grafică modernă și scalabilă.

## 🚀 Lansare Rapidă

### **Metoda 1: Dublu-click pe fișierul .bat**
```
Start_CaptionsUI.bat
```

### **Metoda 2: Din terminal**
```bash
python caption_ui.py
```

## ✨ Funcționalități UI

### 📁 **Selecție Fișiere**
- **Drag & Drop** - Trage fișierele audio direct în interfață
- **Browse Button** - Dialog clasic pentru selecție
- **Formate suportate**: MP3, WAV, M4A, FLAC, OGG, AAC

### ⚙️ **Setări Dinamice**
- **Cuvinte per caption**: 1-5 (slider interactiv)
- **Durată minimă/maximă**: Configurable cu precizie de 0.1s
- **Model Whisper**: tiny, base, small, medium, large

### 🎯 **Presets Rapide**
- **TikTok**: 1 cuvânt, 0.5-2.0s (ultra dinamic)
- **YouTube Shorts**: 2 cuvinte, 0.7-3.0s (dinamic)
- **Standard**: 3 cuvinte, 1.0-4.0s (clasic)

### 📄 **Formate Export**
- ✅ **SRT** - Standard pentru video editoare
- ✅ **VTT** - Web și streaming
- 📊 **JSON** - Pentru dezvoltatori
- 📋 **CSV** - Pentru analiză

### 📂 **Management Folder Export**
- **Selectare folder custom** - Organizează fișierele unde vrei
- **Auto-suggest** - Propune folderul audio-ului ca destinație
- **Folder curent** - Reset rapid la directorul de lucru
- **Deschidere automată** - Acces direct la fișierele generate

### 📊 **Monitoring în Timp Real**
- Progress bar animat
- Log detaliat cu statistici
- Butoane pentru deschiderea folderului de output

## 🎨 **Design UI**

### **Fereastră Scalabilă**
- **Dimensiune minimă**: 800x600
- **Dimensiune implicită**: 900x700
- **Scalare automată**: Toate elementele se adaptează la redimensionare

### **Layout Responsiv**
- **Grid Layout** cu weights pentru scalare
- **Secțiuni organizate** în frame-uri logice
- **Scroll automat** în zona de output

### **Stil Modern**
- **Font Segoe UI** pentru look Windows modern
- **Culori echilibrate** pentru confort vizual
- **Icoane emoji** pentru identificare rapidă
- **Button styles** moderne cu padding

## 🔧 **Structură Fișiere**

```
CAPTIONS_AENEAS/
├── 🎬 caption_ui.py          # UI-ul grafic principal
├── ⚙️ dynamic_captions.py    # Engine-ul de procesare
├── 🚀 Start_CaptionsUI.bat   # Launcher rapid
├── 📖 CAPTIONS_DINAMICE.md   # Ghid comenzi console
├── 🔧 .venv/                 # Environment Python
└── 🎵 [fișierele tale audio + captions generate]
```

## 🛠️ **Workflow Complet**

### **Pas 1**: Lansare
```
Dublu-click pe Start_CaptionsUI.bat
```

### **Pas 2**: Selectare Audio
- Drag & drop fișierul în zona marcată
- SAU folosește butonul "Browse..."

### **Pas 3**: Configurare
- Alege preset rapid (TikTok/YouTube/Standard)
- SAU configurează manual cuvintele și durata

### **Pas 4**: Generare
- Click pe "🚀 Generează Captions"
- Urmărește progresul în zona de output

### **Pas 5**: Export
- Captions-urile se salvează automat
- Click pe "📁 Deschide Folder" pentru a le vedea

## 📈 **Exemplu Output**

```
✅ Succes! Generat 31 captions din 61 cuvinte
📊 Statistici: 2.0 cuvinte/caption, 19.2s durată totală
💾 Fișiere salvate: audio_dynamic.srt, audio_dynamic.vtt
```

## 🔍 **Troubleshooting**

### **UI nu pornește**
- Verifică că Python 3.13+ este instalat
- Rulează manual: `python caption_ui.py`

### **Eroare cu tkinterdnd2**
- Se va folosi UI fără drag&drop (funcțional 100%)
- Folosește butonul Browse în loc de drag&drop

### **FFmpeg warning**
- Captions-urile se vor genera normal
- Pentru audio complex, instalează FFmpeg

## 🎯 **Use Cases**

### **Content Creators**
- Generare rapidă pentru TikTok/Instagram
- Captions dinamice pentru engagement maxim

### **Video Editors**
- Import direct în Premiere/DaVinci/CapCut
- Sincronizare perfectă cu audio

### **Dezvoltatori**
- Export JSON pentru integrare în aplicații
- API Python pentru automatizare

---

**🎬 Gata să creezi captions dinamice incredibile!** 🚀