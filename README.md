# Wi-Fi Environment Analyzer

**作成者**: 古家悠貴（25a31e0014）

周囲のWi-Fi電波をスキャンし、**スペクトラムグラフで見える化**するデスクトップアプリです。  
混雑チャンネルの特定や干渉の確認に役立ちます。

---

## 🚀 起動方法

### 方法1: EXEファイルで起動（推奨）
`dist/WiFiAnalyzer.exe` をダブルクリック。  
> Defenderの警告が出た場合は「詳細情報」→「実行」をクリック。

### 方法2: Pythonで起動（開発者向け）
**環境**: Windows 10/11 (64-bit), Python 3.8〜3.12

```bash
pip install pywifi comtypes pandas matplotlib
python wifi_test.py
```

---

## ✨ 主な機能

| 機能 | 説明 |
| :--- | :--- |
| スペクトラムグラフ | 2.4GHz / 5GHz帯を視覚化。接続中のWi-Fiは赤でハイライト |
| 信号強度フィルター | スライダーで弱い電波を非表示（-100 〜 -20 dBm） |
| グラフクリック詳細 | Wi-Fi波形をクリックして SSID・BSSID・強度などを確認 |
| 自動更新 | 一定間隔でスキャンを繰り返し、リアルタイム監視 |
| マルチアダプター対応 | 複数のWi-Fiアダプターをドロップダウンで切替可能 |

---

## 📖 基本操作

1. **「手動スキャン」** をクリックしてグラフを描画
2. **「自動更新」** をONにするとリアルタイム監視開始
3. **2.4GHz / 5GHz** ラジオボタンで周波数帯を切替
4. **信号強度スライダー** で不要な弱電波を非表示
5. **グラフ上の山をクリック** でWi-Fi詳細を確認

---

## 📊 電波強度（RSSI）の目安

| 強度 (dBm) | 評価 | 状態 |
| :---: | :---: | :--- |
| -50 以上 | 🟢 優秀 | 動画・ゲームに最適 |
| -60 〜 -50 | 🔵 良好 | 安定した通信が可能 |
| -70 〜 -60 | 🟡 普通 | 通常閲覧は問題なし |
| -80 〜 -70 | 🟠 弱い | ルーターに近づくか、チャンネル変更を推奨 |
| -80 未満 | 🔴 非常に弱い | 切断・パケットロスが頻発 |

> 💡 dBmは**0に近いほど強力**です（例: `-50 dBm` > `-80 dBm`）。

---

## 🧪 テスト実行

```bash
python test_verify.py
```

ライブラリの確認・構文チェック・変換ロジック・フィルター動作などを自動検証します。

---

## 📁 プロジェクト構成

```
WiFi-Analyzer/
├── wifi_test.py        ← メインアプリ（GUI & ロジック）
├── test_verify.py      ← 自動テストスクリプト
├── WiFiAnalyzer.spec   ← PyInstallerビルド設定
├── README.md           ← 本ドキュメント
├── dist/
│   └── WiFiAnalyzer.exe  ← 配布用実行ファイル
└── output/             ← 生成成果物
```

---

## 🛠️ 使用技術

| ライブラリ | 用途 |
| :--- | :--- |
| `tkinter` / `ttk` | GUIコンポーネント |
| `pywifi` | Wi-Fiスキャン（Windows WLAN API） |
| `matplotlib` | スペクトラムグラフ描画 |
| `pandas` | データのフィルタリング・ソート |

---

## ❓ よくある問題

- **Wi-Fiが見つからない** → Wi-Fi機能が有効か確認、または管理者権限で実行
- **スキャンが遅い** → アダプターの仕様上、数秒かかるのは正常
- **一部が表示されない** → 信号強度フィルターをリセットし、周波数帯の切替を試す

---

## 🔗 参考リンク

- [pywifi](https://github.com/awkman/pywifi)
- [Matplotlib](https://matplotlib.org/)
- [Microsoft Native Wifi API](https://learn.microsoft.com/en-us/windows/win32/nativewifi/native-wifi-api-sample)
