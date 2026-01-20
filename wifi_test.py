import tkinter as tk
from tkinter import ttk
import pywifi
from pywifi import const
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading
import socket
import subprocess
import math
import sys

try:
    import pythoncom
except ImportError:
    pythoncom = None

class WifiAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wi-Fi Environment Analyzer (White Mode)")
        self.root.geometry("1100x850")
        self.is_scanning = False
        self.auto_scan_active = False
        self.target_band = "2.4GHz"
        self.current_results = []
        self.current_ssid = ""
        self.network_info_list = []  # グラフ上のネットワーク情報リスト

        # データ保持（Persistence）機能: キャッシュとTTL設定
        # キー: "SSID_チャンネル", 値: {"signal": 信号強度, "last_seen": 最終検出時刻, "ssid": SSID, "channel": チャンネル, "band": 周波数帯}
        self.wifi_cache = {}
        self.cache_ttl = 10  # データ保持期間（秒）

        self.info_frame = ttk.Frame(root, padding=5, relief="groove")
        self.info_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.info_label = ttk.Label(self.info_frame, text="接続情報取得中...", font=("MS Gothic", 12, "bold"))
        self.info_label.pack()

        self.ctrl_frame = ttk.Frame(root, padding=5)
        self.ctrl_frame.pack(side=tk.TOP, fill=tk.X)

        # WiFiアダプター選択UI
        ttk.Label(self.ctrl_frame, text="アダプター: ").pack(side=tk.LEFT, padx=5)
        self.adapter_var = tk.StringVar()
        self.adapter_combo = ttk.Combobox(self.ctrl_frame, textvariable=self.adapter_var, state='readonly', width=30)
        self.adapter_combo.pack(side=tk.LEFT, padx=5)
        self.adapter_combo.bind('<<ComboboxSelected>>', self.on_adapter_change)

        self.scan_btn = ttk.Button(self.ctrl_frame, text="手動スキャン", command=self.start_manual_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        self.auto_btn = ttk.Button(self.ctrl_frame, text="自動更新: OFF", command=self.toggle_auto_scan)
        self.auto_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.ctrl_frame, text=" |  周波数帯: ").pack(side=tk.LEFT, padx=5)
        self.band_var = tk.StringVar(value="2.4GHz")
        ttk.Radiobutton(self.ctrl_frame, text="2.4GHz", variable=self.band_var, value="2.4GHz", command=self.refresh_graph_only).pack(side=tk.LEFT)
        ttk.Radiobutton(self.ctrl_frame, text="5GHz", variable=self.band_var, value="5GHz", command=self.refresh_graph_only).pack(side=tk.LEFT)

        self.status_label = ttk.Label(self.ctrl_frame, text="準備完了", foreground="blue")
        self.status_label.pack(side=tk.RIGHT, padx=20)

        self.graph_frame = ttk.Frame(root)
        self.graph_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        plt.style.use("default")
        plt.rcParams['font.family'] = 'MS Gothic'
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.fig.subplots_adjust(bottom=0.15)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # クリックイベントを追加
        self.canvas.mpl_connect('button_press_event', self.on_graph_click)
        self.log_frame = ttk.LabelFrame(root, text="検出ログ", padding=5)
        self.log_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        self.log_text = tk.Text(self.log_frame, height=5, state='disabled', font=("MS Gothic", 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar.set

        self.init_wifi()
        self.update_connection_info()

    def init_wifi(self):
        self.wifi = pywifi.PyWiFi()
        self.interfaces = self.wifi.interfaces()

        if len(self.interfaces) == 0:
            self.log_message("エラー: Wi-Fiインターフェースが見つかりません。")
            self.scan_btn.config(state='disabled')
            self.iface = None
        else:
            # アダプター一覧を作成
            adapter_names = []
            for idx, iface in enumerate(self.interfaces):
                adapter_names.append(f"{idx}: {iface.name()}")

            # コンボボックスに設定
            self.adapter_combo['values'] = adapter_names

            # デフォルトは最後のアダプター（通常、外部アダプターは後に認識される）
            default_index = len(self.interfaces) - 1
            self.adapter_combo.current(default_index)
            self.iface = self.interfaces[default_index]

            self.log_message(f"初期化完了: {len(self.interfaces)} 個のアダプター検出")
            self.log_message(f"選択中: {self.iface.name()}")

    def on_adapter_change(self, event=None):
        """アダプター選択変更時の処理"""
        selected = self.adapter_combo.current()
        if 0 <= selected < len(self.interfaces):
            self.iface = self.interfaces[selected]
            self.log_message(f"アダプター切り替え: {self.iface.name()}")
            # キャッシュをクリア
            self.wifi_cache.clear()
            self.update_connection_info()

    def get_current_connection_info(self):
        ssid = "未接続"
        ip = "取得不可"
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except: pass
        try:
            output = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('cp932', errors='ignore')
            for line in output.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ssid = parts[1].strip()
                        break
        except: pass
        return ssid, ip

    def update_connection_info(self):
        ssid, ip = self.get_current_connection_info()
        self.current_ssid = ssid
        self.info_label.config(text=f"現在の接続: SSID [{ssid}]  /  IP [{ip}]")

    def log_message(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        print(f"[LOG] {msg}")

    def frequency_to_channel(self, freq_value):
        if freq_value is None: return None, None

        # 周波数の単位を正規化
        freq_mhz = freq_value
        if freq_value > 100_000_000:
            freq_mhz = freq_value / 1_000_000
        elif freq_value > 100_000:
            freq_mhz = freq_value / 1_000

        # 2.4GHz帯の正確なマッピング
        channels_24ghz = {
            2412: 1, 2417: 2, 2422: 3, 2427: 4, 2432: 5,
            2437: 6, 2442: 7, 2447: 8, 2452: 9, 2457: 10,
            2462: 11, 2467: 12, 2472: 13, 2484: 14
        }

        # 5GHz帯の正確なマッピング
        channels_5ghz = {
            5180: 36, 5200: 40, 5220: 44, 5240: 48,
            5260: 52, 5280: 56, 5300: 60, 5320: 64,
            5500: 100, 5520: 104, 5540: 108, 5560: 112, 5580: 116,
            5600: 120, 5620: 124, 5640: 128, 5660: 132, 5680: 136, 5700: 140,
            5720: 144, 5745: 149, 5765: 153, 5785: 157, 5805: 161, 5825: 165,
            5845: 169, 5865: 173, 5885: 177
        }

        # 2.4GHz帯のチャンネル判定（最も近い周波数を探す）
        if 2400 <= freq_mhz <= 2500:
            min_diff = float('inf')
            best_ch = None
            for freq, ch in channels_24ghz.items():
                diff = abs(freq_mhz - freq)
                if diff < min_diff:
                    min_diff = diff
                    best_ch = ch
            if min_diff <= 3:  # 3MHz以内の誤差を許容
                return best_ch, "2.4GHz"

        # 5GHz帯のチャンネル判定（最も近い周波数を探す）
        elif 5000 <= freq_mhz <= 6000:
            min_diff = float('inf')
            best_ch = None
            for freq, ch in channels_5ghz.items():
                diff = abs(freq_mhz - freq)
                if diff < min_diff:
                    min_diff = diff
                    best_ch = ch
            if min_diff <= 10:  # 10MHz以内の誤差を許容
                return best_ch, "5GHz"

        return None, None

    def on_graph_click(self, event):
        """グラフクリック時のイベントハンドラ"""
        if event.inaxes != self.ax:
            return

        # クリック位置に最も近いネットワークを検索
        if not self.network_info_list:
            return

        min_dist = float('inf')
        selected_network = None

        for network in self.network_info_list:
            # データ座標での距離を計算
            dx = event.xdata - network["x"]
            dy = event.ydata - network["y"]
            dist = (dx**2 + dy**2) ** 0.5

            if dist < min_dist:
                min_dist = dist
                selected_network = network

        # 距離が十分近い場合のみ情報を表示（クリック範囲を制限）
        threshold = 5 if self.band_var.get() == "2.4GHz" else 15
        if min_dist < threshold:
            self.show_network_info(selected_network)

    def show_network_info(self, network):
        """ネットワーク詳細情報を表示"""
        info_window = tk.Toplevel(self.root)
        info_window.title(f"ネットワーク情報: {network['ssid']}")
        info_window.geometry("400x300")
        info_window.resizable(False, False)

        # ウィンドウを中央に配置
        info_window.transient(self.root)
        info_window.grab_set()

        # 情報フレーム
        info_frame = ttk.Frame(info_window, padding=20)
        info_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        title_label = ttk.Label(info_frame, text=network['ssid'],
                               font=("MS Gothic", 14, "bold"),
                               foreground=network['color'] if not network['is_connected'] else "#D32F2F")
        title_label.pack(pady=(0, 15))

        # 接続状態
        if network['is_connected']:
            status_label = ttk.Label(info_frame, text="● 接続中",
                                    font=("MS Gothic", 10, "bold"),
                                    foreground="#D32F2F")
            status_label.pack(pady=5)

        # 詳細情報
        details_frame = ttk.Frame(info_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        info_items = [
            ("SSID名:", network['ssid']),
            ("周波数帯:", network['band']),
            ("チャンネル:", f"Ch {network['channel']}"),
            ("信号強度:", f"{network['signal']} dBm"),
            ("信号品質:", self.get_signal_quality(network['signal']))
        ]

        for i, (label, value) in enumerate(info_items):
            label_widget = ttk.Label(details_frame, text=label,
                                    font=("MS Gothic", 10, "bold"))
            label_widget.grid(row=i, column=0, sticky=tk.W, pady=5, padx=(0, 10))

            value_widget = ttk.Label(details_frame, text=value,
                                    font=("MS Gothic", 10))
            value_widget.grid(row=i, column=1, sticky=tk.W, pady=5)

        # 閉じるボタン
        close_btn = ttk.Button(info_frame, text="閉じる", command=info_window.destroy)
        close_btn.pack(pady=(15, 0))

        self.log_message(f"ネットワーク情報表示: {network['ssid']}")

    def get_signal_quality(self, signal_dbm):
        """信号強度から品質を判定"""
        if signal_dbm >= -50:
            return "優秀 (Excellent)"
        elif signal_dbm >= -60:
            return "良好 (Good)"
        elif signal_dbm >= -70:
            return "普通 (Fair)"
        elif signal_dbm >= -80:
            return "弱い (Weak)"
        else:
            return "非常に弱い (Very Weak)"

    def start_manual_scan(self):
        if not self.is_scanning:
            self.update_connection_info()
            threading.Thread(target=self.scan_process, daemon=True).start()

    def toggle_auto_scan(self):
        if self.auto_scan_active:
            self.auto_scan_active = False
            self.auto_btn.config(text="自動更新: OFF")
            self.status_label.config(text="自動更新停止")
        else:
            self.auto_scan_active = True
            self.auto_btn.config(text="自動更新: ON")
            self.start_manual_scan()

    def refresh_graph_only(self):
        """周波数帯切り替え時にキャッシュデータからグラフを再描画"""
        # 生データ(current_results)ではなく、キャッシュから直接描画
        # これにより、帯域切り替え時もキャッシュが維持される
        current_time = time.time()
        target_band = self.band_var.get()

        # 期限切れデータを削除
        expired_keys = [
            key for key, value in self.wifi_cache.items()
            if current_time - value["last_seen"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.wifi_cache[key]

        # キャッシュから対象帯域のデータを抽出
        data = []
        for key, value in self.wifi_cache.items():
            if value["band"] == target_band:
                data.append({
                    "channel": value["channel"],
                    "signal": value["signal"],
                    "ssid": value["ssid"],
                    "band": value["band"]
                })

        df = pd.DataFrame(data)
        self.update_graph(df, target_band)

    def scan_process(self):
        if pythoncom:
            pythoncom.CoInitialize()

        self.is_scanning = True
        self.root.after(0, lambda: self.status_label.config(text="スキャン中...", foreground="red"))
        self.root.after(0, lambda: self.scan_btn.config(state='disabled'))

        try:
            print("スキャン開始...")
            self.iface.scan()
            time.sleep(1)  # スキャン結果待ち時間を短縮（元は4秒）
            results = self.iface.scan_results()

            print(f"スキャン完了: 生データ {len(results)} 件")
            self.current_results = results
            self.process_results(results)

        except Exception as e:
            err_msg = f"スキャンエラー: {e}"
            print(err_msg)
            self.root.after(0, lambda: self.log_message(err_msg))

        finally:
            self.is_scanning = False
            self.root.after(0, lambda: self.scan_btn.config(state='normal'))
            self.root.after(0, lambda: self.status_label.config(text="完了", foreground="green"))

            if self.auto_scan_active:
                time.sleep(0.1)  # 次スキャンまでの待機を短縮（元は2秒）
                threading.Thread(target=self.scan_process, daemon=True).start()

    def process_results(self, results):
        """スキャン結果をキャッシュにマージし、期限切れデータを削除後、グラフを更新"""
        current_time = time.time()

        # ステップ1: スキャン結果をキャッシュに更新（両帯域とも処理）
        for network in results:
            ssid = getattr(network, "ssid", "")
            if not ssid:
                continue

            freq_val = getattr(network, "freq", None) or getattr(network, "frequency", None)
            signal = getattr(network, "signal", -100)
            channel, band = self.frequency_to_channel(freq_val)

            if channel is None or band is None:
                continue

            key = f"{ssid}_{channel}"
            self.wifi_cache[key] = {
                "signal": signal,
                "last_seen": current_time,
                "ssid": ssid,
                "channel": channel,
                "band": band
            }

        # ステップ2: 期限切れデータ（TTL超過）をキャッシュから削除
        expired_keys = [
            key for key, value in self.wifi_cache.items()
            if current_time - value["last_seen"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.wifi_cache[key]

        # ステップ3: 現在の表示対象帯域でフィルタリング
        target_band = self.band_var.get()
        data = []
        unique_check = set()

        for key, value in self.wifi_cache.items():
            if value["band"] != target_band:
                continue

            # 重複チェック（同じSSID+チャンネルの組み合わせ）
            if key in unique_check:
                continue
            unique_check.add(key)

            data.append({
                "channel": value["channel"],
                "signal": value["signal"],
                "ssid": value["ssid"],
                "band": value["band"]
            })

        print(f"{target_band}帯の有効データ: {len(data)} 件（キャッシュ総数: {len(self.wifi_cache)}）")
        df = pd.DataFrame(data)
        self.root.after(0, lambda: self.update_graph(df, target_band))

    def _channel_axis(self, band):
        if band == "2.4GHz":
            return list(np_linspace(1, 14, 200)), list(range(1, 15)), (1, 14)
        return list(np_linspace(34, 179, 500)), list(range(34, 180, 8)), (34, 179)

    def _curve(self, x_axis, center_ch, peak_dbm, band):
        base = -100
        spread = 2.5 if band == "2.4GHz" else 5.0
        y_vals = []
        for x in x_axis:
            delta = abs(x - center_ch)
            if delta > spread * 2:
                y = base
            else:
                y = base + (peak_dbm - base) * math.exp(-0.5 * (delta / (spread/2.5)) ** 2)
            y_vals.append(max(y, base))
        return y_vals

    def update_graph(self, df, band):
        """キャッシュから作成したDataFrameでグラフを更新（スマートラベル配置対応）"""
        # ★白背景設定
        plt.style.use("default")
        plt.rcParams['font.family'] = 'MS Gothic'

        self.ax.clear()
        self.network_info_list = []  # ネットワーク情報リストをクリア

        # 軸データの生成
        x_min, x_max = (1, 14) if band == "2.4GHz" else (34, 179)
        step = (x_max - x_min) / 400
        x_axis = [x_min + i * step for i in range(401)]

        # グリッド設定（見やすいグレー）
        self.ax.grid(True, linestyle="--", alpha=0.5, color="#999999")
        self.ax.set_ylim(-100, -20)
        self.ax.set_xlim(x_min, x_max)

        if df.empty:
            self.ax.text((x_min+x_max)/2, -60, "No Wi-Fi Found", ha="center", color="#333", fontsize=14)
            self.canvas.draw()
            return

        connected_ssid = (self.current_ssid or "").strip()
        colors = plt.cm.tab10.colors

        # ★チャンネル順（昇順）でソート - ラベル重なり回避のため
        df = df.sort_values(by=["channel", "signal"], ascending=[True, False]).reset_index(drop=True)

        # ★描画済みラベル位置を記録（重なり回避用）
        label_positions = []  # [(x, y), ...]

        # ラベル重なり判定のしきい値
        ch_threshold = 3 if band == "2.4GHz" else 10  # チャンネル近接しきい値（拡大）
        y_offset_step = 10  # Y方向オフセット量 (dBm)（拡大）

        for idx, row in df.iterrows():
            is_connected = (row["ssid"] == connected_ssid)
            color = colors[idx % len(colors)]

            if is_connected:
                color = "#D32F2F"

            y_curve = self._curve(x_axis, row["channel"], row["signal"], band)

            z = 10 if is_connected else 5

            self.ax.fill_between(x_axis, y_curve, -100, color=color, alpha=0.3, zorder=z)
            self.ax.plot(x_axis, y_curve, color=color, linewidth=2.5 if is_connected else 1.5, zorder=z+1)

            # ★改善されたラベル: SSID (Ch番号, 信号強度dBm)
            label_text = f"{row['ssid']}\n(Ch{row['channel']}, {int(row['signal'])}dBm)"

            # ★スマートラベル配置: Y座標オフセット計算
            base_x = row["channel"]
            base_y = row["signal"] + 3
            final_y = base_y

            # 既存ラベルとの重なりをチェックし、必要に応じてオフセット
            offset_count = 0
            for prev_x, prev_y in label_positions:
                ch_diff = abs(base_x - prev_x)
                y_diff = abs(final_y - prev_y)

                # チャンネルが近く、かつY座標も近い場合はオフセット
                if ch_diff <= ch_threshold and y_diff < y_offset_step * 1.5:
                    offset_count += 1
                    final_y = base_y + (offset_count * y_offset_step)

            # Y座標が上限を超えないように制限
            final_y = min(final_y, -22)

            # 描画位置を記録
            label_positions.append((base_x, final_y))

            # ★ネットワーク情報を保存（クリック検出用）
            self.network_info_list.append({
                "ssid": row["ssid"],
                "channel": row["channel"],
                "signal": int(row["signal"]),
                "band": band,
                "x": base_x,
                "y": final_y,
                "is_connected": is_connected,
                "color": color
            })

            # ★フォントサイズと色分け
            font_weight = "bold" if is_connected else "normal"
            font_size = 8 if is_connected else 7
            # 接続中のネットワークは赤背景
            bg_color = "#FFEBEE" if is_connected else "white"

            # クリック可能なラベル（pickerを有効化）
            text_obj = self.ax.text(base_x, final_y, label_text,
                         color="black",
                         fontsize=font_size,
                         fontweight=font_weight,
                         ha="center", va="bottom",
                         zorder=z+5,
                         rotation=0,
                         picker=True,
                         bbox=dict(boxstyle="round,pad=0.3", fc=bg_color, ec=color, linewidth=1.2, alpha=0.9))
            text_obj.set_gid(str(idx))  # インデックスを保存

        if band == "2.4GHz":
            self.ax.set_xticks(range(1, 15))
        else:
            self.ax.set_xticks(range(36, 180, 8))

        self.ax.set_xlabel("チャンネル", fontsize=12)
        self.ax.set_ylabel("信号強度 (dBm)", fontsize=12)
        self.ax.set_title(f"Wi-Fi スペクトラム ({band})", fontsize=14, fontweight="bold")

        self.canvas.draw()
        msg = f"{band}帯: {len(df)} 件検出"
        self.log_message(msg)

def np_linspace(start, stop, num):
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]

if __name__ == "__main__":
    root = tk.Tk()
    app = WifiAnalyzerApp(root)
    root.mainloop()