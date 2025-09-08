# melonDS-launcher

[English version](./README.md)

一個以 Python + Tkinter/ttkbootstrap 寫成的 **melonDS 模擬器啟動器 (Launcher)**。  
提供圖形化介面：掃描 ROM、顯示封面與標題、釘選常玩、雙擊開啟等。

> ⚠️ 本專案與 melonDS 官方無關，僅為個人開發的工具程式。  
> 本專案 **不包含任何 ROM 或遊戲圖片**；使用者需自行提供，並負責其合法性。

[Demo.gif](./images/demo.gif)
<a href="images/demo.gif">
    <img src="images/demo.gif" width="1000" alt="GUI Demo">
</a>  

---

## 功能特色
- ✅ Grid / List 兩種檢視、比例縮放
- ✅ 釘選遊戲、只顯示釘選
- ✅ 顯示 ROM 內部標題與 Game ID
- ✅ 右側資訊面板：封面、路徑、ID
- ✅ 中英切換（zh/en）
- ✅ 一鍵開啟 melonDS 並載入所選 ROM
- ✅ 深色 UI / 捲動優化

---

## 安裝 / 使用範例

### 方法一：
1. 至 [Releases](https://github.com/LeviChen1126/melonDS-launcher/releases) 下載最新的 `melonDS-launcher.exe`  
2. 直接雙擊執行 `melonDS-launcher.exe`
   - 首次啟動可能需要幾秒鐘（因為 Onefile 會先解壓到暫存資料夾）。
   - 如果防毒軟體跳警告，請先確認來源安全再允許。

### 方法二：
1. 下載或 Clone：
   ```bash
   git clone https://github.com/LeviChen1126/melonDS-launcher.git
   cd melonDS-launcher
   ```

2. 安裝依賴項：
   ```bash
   pip install -r requirements.txt
   ```

3. 執行：
   ```bash
   python melonDS-launcher.py
   ```

> ⚠️ 不論使用哪種方式，都需自行安裝 [melonDS](https://melonds.kuribo64.net/) 並在程式內設定執行檔路徑。

---

## 專案結構
```bash
─── melonDS-launcher/
   ├── melonDS-launcher.py        # 主程式
   ├── assets/                    # 程式圖示
   │   ├── nds.ico
   │   ├── nds.png
   │   └── lang.png, pin.png, grid.png, list.png, browse.png ...
   ├── config/                    # 執行後自動產生：使用者設定、名稱/封面映射
   │   ├── melonds_launcher_config.json
   │   ├── covers_map.json
   │   └── titles_map.json
   ├── covers/                    # 執行後自動產生：封面圖存放位置
   ├── requirements.txt
   ├── LICENSE
   ├── .gitignore
   └── .gitattributes
```

---

## 版權與致謝
- 本專案 **不包含** 任何任天堂 ROM 或遊戲圖像；使用者需自行提供並確保合法性
- 本專案與 melonDS 官方無關；melonDS 由原作者依 **GPLv3** 授權釋出
- 本專案程式碼以 [MIT License](./LICENSE) 授權
- [melonDS](https://github.com/melonDS-emu/melonDS)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/en/latest/)
