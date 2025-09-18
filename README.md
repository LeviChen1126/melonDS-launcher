# melonDS-launcher

[中文版本](./README_zh-TW.md)

A **Nintendo DS emulator launcher (GUI)** built with **PySide6 (Qt)**.  
It provides a graphical interface to scan ROMs, display covers and titles, pin frequently played games, and launch them with a double click.  


> ⚠️ This project is **not affiliated with the official melonDS team**, it is a personal utility tool.  
> **No ROMs or game artwork are included** — users must provide their own and ensure legality.

[Demo.gif](./images/demo.gif)  
[Demo.mp4](./images/Demo.mp4)  

<a href="images/demo.gif">
    <img src="images/demo.gif" width="1000" alt="GUI Demo">
</a>  

---

## Features
- ✅ Grid / List view modes with zoom scaling  
- ✅ Pin games / filter to show only pinned ones  
- ✅ Automatic Online Cover Download
- ✅ Display internal ROM Title and Game ID  
- ✅ NDS icon included in the launcher  
- ✅ Right-side info panel: cover, path, ID  
- ✅ Language toggle (zh/en)  
- ✅ One-click to launch the selected emulator with a chosen ROM (not limited to melonDS, works with any DS emulator supporting CLI launch)  
- ✅ **Thumbnail system:**  
  - Low-resolution thumbnails are auto-generated for the game list (faster loading)  
  - The right-side detail panel displays high-resolution covers  
  - Thumbnail size can be configured with `thumb_size`  
- ✅ Dark UI theme / smooth scrolling  

---

## Installation / Usage Example

### Method 1:
1. Download the latest `melonDS-Launcher.exe` from [Releases](https://github.com/LeviChen1126/melonDS-launcher/releases).  
2. Double-click `melonDS-Launcher.exe` to run.  
   - The first startup may take a few seconds.  
   - If your antivirus shows a warning, please verify the source and allow execution.  

### Method 2:
1. Clone this repository:
   ```bash
   git clone https://github.com/LeviChen1126/melonDS-launcher.git
   cd melonDS-launcher
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python melonDS-launcher.py
   ```

> ⚠️ In either case, you must install a DS emulator (e.g. [melonDS](https://melonds.kuribo64.net/)) separately and configure the executable path within this program.

---

## Project Structure
```bash
─── melonDS-launcher/
   ├── melonDS-launcher.py   # Main script (PySide6)
   ├── assets/                              # Program icons
   │   ├── nds.ico
   │   ├── nds.png
   │   └── lang.png, pin.png, grid.png, list.png, browse.png ...
   ├── config/                              # Auto-generated: user settings, cover/title mapping
   │   ├── melonds_launcher_config.json
   │   ├── covers_map.json
   │   └── titles_map.json
   ├── covers/                              # Auto-generated: cover image storage
   │   └── .thumb/                          # Auto-generated thumbnails
   ├── requirements.txt
   ├── LICENSE
   ├── .gitignore
   └── .gitattributes
```

---

## Version Differences
- v1.x → Tkinter + ttkbootstrap interface  
- v2.x → PySide6 (Qt) interface 

---

## Credits & Acknowledgments
- This project **does not include** any Nintendo ROMs or game artwork; users must provide their own legally obtained resources.  
- This project is **not affiliated with melonDS**; the melonDS emulator is released under **GPLv3**.  
- The code of this project is licensed under the [MIT License](./LICENSE).  
- [melonDS](https://github.com/melonDS-emu/melonDS)  
- [PySide6](https://doc.qt.io/qtforpython/)  
