# TwinPics  
Find duplicates of images – simple, fast, and lightweight.

TwinPics is a Python tool which hunts down **duplicate images** from a selected folder and shows you which ones are basically evil twins.  
No Python needed if you just grab the `.exe` from [Releases](../../releases](https://github.com/LordPrettyRustyRyan/TwinPics/releases/tag/v2.0.0)).

## Features:
- One-click folder Selection and Scans.
- Finds duplicate images using smart hash comparisons.
- Lists duplicates so you can delete them.
- Delete duplicates directly from the app
- One-click “Delete All Duplicates”
- Works on JPG, JPEG, PNG
- Saves your disk space

## Stack
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-FF6F00?style=for-the-badge)
![Pillow](https://img.shields.io/badge/Pillow-8A2BE2?style=for-the-badge)

## Download
[Get TwinPics.v2.exe here]([../../releases/latest](https://github.com/LordPrettyRustyRyan/TwinPics/releases/download/v2.0.0/TwinPics.v2.exe))  

---

<img width="940" height="588" alt="folder picker" src="https://github.com/user-attachments/assets/87e7eb41-dabf-4f16-8f0f-c0bb760d7943" />
<img width="1185" height="847" alt="Screenshot 2025-12-27 162451" src="https://github.com/user-attachments/assets/e62e68ab-47e9-4f48-9410-dc9a2eb7d190" />
<img width="1920" height="1018" alt="Screenshot (1914)" src="https://github.com/user-attachments/assets/fd8e4b05-319a-4f63-aebf-710d9a6ac797" />

---

## Usage
### Option A: Use the `.exe`
1. Download **TwinPics.v2.exe** from [Releases](../../releases](https://github.com/LordPrettyRustyRyan/TwinPics/releases/tag/v2.0.0)).
2. Run it.  
3. Pick a folder → boom, twins exposed.  

### Option B: Run from source (requires Python 3.8+)
```bash
git clone https://github.com/LordPrettyRustyRyan/TwinPics.git
cd TwinPics
pip install -r requirements.txt
python TwinPics.py
