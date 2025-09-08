# melonDS-launcher

[中文版本](./README_zh-TW.md)

A **melonDS emulator launcher (GUI)** built with Python + Tkinter/ttkbootstrap.  
It provides a graphical interface to scan ROMs, display covers and titles, pin frequently played games, and launch them with a double click.

> ⚠️ This project is **not affiliated with the official melonDS team**, it is a personal utility tool.  
> **No ROMs or game images are included** — users must provide their own and ensure legality.

<a href="images/demo.gif">
    <img src="images/demo.gif" width="1000" alt="GUI Demo">
</a>  

---

## Features
- ✅ Grid / List view modes with zoom scaling
- ✅ Pin games and filter to show only pinned ones
- ✅ Display internal NDS Title and GameCode (read from ROM header)
- ✅ Right-side info panel: cover, path, ID
- ✅ Language toggle (zh/en), using `lang.png`
- ✅ One-click to launch melonDS with the selected ROM
- ✅ Dark UI theme / smooth scrolling / DPI awareness (Windows)

---

## Installation / Usage Example

### Method 1:
1. Download the latest `melonDS-launcher.exe` from [Releases](https://github.com/<YOUR_GITHUB>/melonDS-launcher/releases).  
2. Double-click `melonDS-launcher.exe` to run.  
   - The first startup may take a few seconds (due to Onefile extraction).  
   - If your antivirus shows a warning, please verify the source and allow execution.  

### Method 2:
1. Clone this repository:
   ```bash
   git clone https://github.com/<YOUR_GITHUB>/melonDS-launcher.git
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

> ⚠️ In either case, you must install [melonDS](https://melonds.kuribo64.net/) separately and configure the executable path within this program.

---

## Project Structure
```bash
─── melonDS-launcher/
   ├── melonDS-launcher.py        # Main script
   ├── assets/                    # Program icons
   │   ├── nds.ico
   │   ├── nds.png
   │   └── lang.png, pin.png, grid.png, list.png, browse.png ...
   ├── config/                    # Auto-generated: user settings, cover/title mapping
   │   ├── melonds_launcher_config.json
   │   ├── covers_map.json
   │   └── titles_map.json
   ├── covers/                    # Auto-generated: cover image storage
   ├── requirements.txt
   ├── LICENSE
   ├── .gitignore
   └── .gitattributes
```

---

## Credits & Acknowledgments
- This project **does not include** any Nintendo ROMs or game artwork; users must provide their own legally obtained resources
- This project is **not affiliated with melonDS**; the melonDS emulator is released under **GPLv3**
- The code of this project is licensed under the [MIT License](./LICENSE)
- [melonDS](https://github.com/melonDS-emu/melonDS)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/en/latest/)
