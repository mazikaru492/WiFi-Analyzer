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
        self.info_window = None  # ネットワーク情報表示ウィンドウ（再利用用）
        self.info_widgets = {}  # 情報ウィンドウ内のウィジェット参照

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

        # 信号強度フィルターフレーム
        self.filter_frame = ttk.Frame(root, padding=5)
        self.filter_frame.pack(side=tk.TOP, fill=tk.X, padx=5)

        ttk.Label(self.filter_frame, text="信号強度フィルター:", font=("MS Gothic", 10)).pack(side=tk.LEFT, padx=5)

        self.signal_filter_var = tk.IntVar(value=-100)  # デフォルトは全表示（-100 dBm以上）
        self.signal_filter_scale = ttk.Scale(
            self.filter_frame, from_=-100, to=-20,
            orient=tk.HORIZONTAL, length=250,
            variable=self.signal_filter_var,
            command=self.on_signal_filter_change
        )
        self.signal_filter_scale.pack(side=tk.LEFT, padx=5)

        self.filter_label = ttk.Label(self.filter_frame, text="-100 dBm 以上を表示", font=("MS Gothic", 10), width=22)
        self.filter_label.pack(side=tk.LEFT, padx=5)

        self.filter_count_label = ttk.Label(self.filter_frame, text="", foreground="gray", font=("MS Gothic", 9))
        self.filter_count_label.pack(side=tk.LEFT, padx=5)

        self.filter_reset_btn = ttk.Button(self.filter_frame, text="リセット", command=self.reset_signal_filter)
        self.filter_reset_btn.pack(side=tk.LEFT, padx=5)

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

    def decode_ssid(self, ssid_raw):
        """SSIDをデコードして正しい文字列に変換する"""
        if ssid_raw is None:
            return ""

        # 既に文字列の場合
        if isinstance(ssid_raw, str):
            # 文字化けしている可能性があるSSIDを修正
            # Latin-1でエンコードされた文字列をUTF-8としてデコード
            try:
                # 文字化けしているSSIDを修正するため、latin-1でバイト列に戻してUTF-8でデコード
                fixed = ssid_raw.encode('latin-1').decode('utf-8')
                return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

            # cp932でのデコードを試みる
            try:
                fixed = ssid_raw.encode('latin-1').decode('cp932')
                return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

            # そのまま返す
            return ssid_raw

        # バイト列の場合
        if isinstance(ssid_raw, bytes):
            # UTF-8でデコードを試みる
            try:
                return ssid_raw.decode('utf-8')
            except UnicodeDecodeError:
                pass

            # cp932でデコードを試みる
            try:
                return ssid_raw.decode('cp932')
            except UnicodeDecodeError:
                pass

            # latin-1でデコード（最終手段）
            return ssid_raw.decode('latin-1', errors='replace')

        return str(ssid_raw)

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
            # netshコマンドの出力をバイト列として取得
            raw_output = subprocess.check_output("netsh wlan show interfaces", shell=True)

            # UTF-8でデコードを試み、失敗したらcp932（Shift-JIS）を使用
            try:
                output = raw_output.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    output = raw_output.decode('cp932', errors='replace')
                except:
                    output = raw_output.decode('latin-1', errors='replace')

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

        # クリック位置に近いネットワークを検索
        if not self.network_info_list:
            self.log_message("ネットワーク情報がありません")
            return

        # X軸とY軸のスケールを正規化するための係数
        band = self.band_var.get()
        x_range = 13 if band == "2.4GHz" else 145
        y_range = 80  # dBm範囲

        # しきい値内のすべてのネットワークを収集
        threshold = 0.20  # 20%の範囲内
        nearby_networks = []

        for network in self.network_info_list:
            # 正規化された距離を計算（0-1スケール）
            dx = (event.xdata - network["x"]) / x_range
            dy = (event.ydata - network["y"]) / y_range
            dist = (dx**2 + dy**2) ** 0.5

            # チャンネル差も考慮（ラベルをクリックしやすくする）
            ch_diff = abs(event.xdata - network["x"])

            if dist < threshold or ch_diff <= 2.5:
                nearby_networks.append((dist, network))

        if not nearby_networks:
            return

        # 距離でソート
        nearby_networks.sort(key=lambda x: x[0])

        if len(nearby_networks) == 1:
            # 1つだけなら直接表示
            self.show_network_info(nearby_networks[0][1])
        else:
            # 複数ある場合は選択メニューを表示
            self.show_network_selection_menu(event, [n[1] for n in nearby_networks])

    def show_network_selection_menu(self, event, networks):
        """複数のネットワークから選択するポップアップメニューを表示"""
        menu = tk.Menu(self.root, tearoff=0, font=("MS Gothic", 10))

        for network in networks:
            # 接続中のネットワークにはマークを付ける
            label = f"{'● ' if network['is_connected'] else ''}{network['ssid']} (Ch{network['channel']}, {network['signal']}dBm)"
            menu.add_command(
                label=label,
                command=lambda n=network: self.show_network_info(n)
            )

        # マウス位置にメニューを表示
        try:
            # キャンバス上の座標をスクリーン座標に変換
            canvas_widget = self.canvas.get_tk_widget()
            x_screen = canvas_widget.winfo_rootx() + int(event.x)
            y_screen = canvas_widget.winfo_rooty() + int(event.y)
            menu.tk_popup(x_screen, y_screen)
        except:
            pass
        finally:
            menu.grab_release()

    def show_network_info(self, network):
        """ネットワーク詳細情報を表示（既存ウィンドウがあれば再利用）"""

        # ウィンドウが存在しない、または閉じられている場合は新規作成
        if self.info_window is None or not self.info_window.winfo_exists():
            self._create_info_window()

        # ウィンドウの内容を更新
        self._update_info_content(network)

        # ウィンドウを前面に表示
        self.info_window.lift()
        self.info_window.focus_set()

        self.log_message(f"ネットワーク情報表示: {network['ssid']}")

    def _create_info_window(self):
        """情報表示ウィンドウを新規作成"""
        self.info_window = tk.Toplevel(self.root)
        self.info_window.title("ネットワーク情報")
        self.info_window.geometry("420x320")
        self.info_window.resizable(False, False)
        self.info_window.configure(bg="white")

        # 情報フレーム
        info_frame = tk.Frame(self.info_window, bg="white", padx=20, pady=20)
        info_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル（SSID名）
        self.info_widgets['title'] = tk.Label(info_frame, text="",
                                              font=("MS Gothic", 14, "bold"),
                                              fg="#333333", bg="white")
        self.info_widgets['title'].pack(pady=(0, 10))

        # 接続状態ラベル
        self.info_widgets['status'] = tk.Label(info_frame, text="",
                                               font=("MS Gothic", 10, "bold"),
                                               fg="#D32F2F", bg="white")
        self.info_widgets['status'].pack(pady=5)

        # 区切り線
        separator = tk.Frame(info_frame, height=2, bg="#CCCCCC")
        separator.pack(fill=tk.X, pady=10)

        # 詳細情報フレーム
        details_frame = tk.Frame(info_frame, bg="white")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 情報項目のラベルと値ウィジェットを作成
        labels = ["SSID名:", "周波数帯:", "チャンネル:", "信号強度:", "信号品質:"]
        self.info_widgets['values'] = []

        for i, label_text in enumerate(labels):
            label_widget = tk.Label(details_frame, text=label_text,
                                    font=("MS Gothic", 10, "bold"),
                                    fg="#555555", bg="white", anchor="w")
            label_widget.grid(row=i, column=0, sticky=tk.W, pady=4, padx=(0, 15))

            value_widget = tk.Label(details_frame, text="",
                                    font=("MS Gothic", 10),
                                    fg="#000000", bg="white", anchor="w")
            value_widget.grid(row=i, column=1, sticky=tk.W, pady=4)
            self.info_widgets['values'].append(value_widget)

        # 閉じるボタン
        close_btn = tk.Button(info_frame, text="閉じる", command=self._close_info_window,
                              font=("MS Gothic", 10), bg="#4CAF50", fg="white",
                              activebackground="#45a049", activeforeground="white",
                              padx=20, pady=5, relief="flat", cursor="hand2")
        close_btn.pack(pady=(20, 0))

    def _update_info_content(self, network):
        """情報表示ウィンドウの内容を更新"""
        # タイトル更新
        self.info_window.title(f"ネットワーク情報: {network['ssid']}")

        # SSID名と色を更新
        title_color = "#D32F2F" if network['is_connected'] else "#333333"
        self.info_widgets['title'].config(text=network['ssid'], fg=title_color)

        # 接続状態を更新
        if network['is_connected']:
            self.info_widgets['status'].config(text="● 現在接続中")
        else:
            self.info_widgets['status'].config(text="")

        # 詳細情報を更新
        values = [
            network['ssid'],
            network['band'],
            f"Ch {network['channel']}",
            f"{network['signal']} dBm",
            self.get_signal_quality(network['signal'])
        ]

        for i, value in enumerate(values):
            self.info_widgets['values'][i].config(text=value)

    def _close_info_window(self):
        """情報表示ウィンドウを閉じる"""
        if self.info_window is not None:
            self.info_window.destroy()
            self.info_window = None

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

    def on_signal_filter_change(self, value):
        """信号強度フィルタースライダー変更時のハンドラ"""
        threshold = int(float(value))
        self.signal_filter_var.set(threshold)
        self.filter_label.config(text=f"{threshold} dBm 以上を表示")
        self.refresh_graph_only()

    def reset_signal_filter(self):
        """信号強度フィルターをリセット（全表示に戻す）"""
        self.signal_filter_var.set(-100)
        self.signal_filter_scale.set(-100)
        self.filter_label.config(text="-100 dBm 以上を表示")
        self.refresh_graph_only()

    def refresh_graph_only(self):
        """周波数帯切り替え時にキャッシュデータからグラフを再描画"""
        # 生データ(current_results)ではなく、キャッシュから直接描画
        # これにより、帯域切り替え時もキャッシュが維持される
        current_time = time.time()
        target_band = self.band_var.get()
        signal_threshold = self.signal_filter_var.get()

        # 期限切れデータを削除
        expired_keys = [
            key for key, value in self.wifi_cache.items()
            if current_time - value["last_seen"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.wifi_cache[key]

        # キャッシュから対象帯域のデータを抽出（信号強度フィルター適用）
        data = []
        total_band_count = 0
        for key, value in self.wifi_cache.items():
            if value["band"] == target_band:
                total_band_count += 1
                if value["signal"] >= signal_threshold:
                    data.append({
                        "channel": value["channel"],
                        "signal": value["signal"],
                        "ssid": value["ssid"],
                        "band": value["band"]
                    })

        df = pd.DataFrame(data)
        self.update_graph(df, target_band, total_band_count)

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
            ssid_raw = getattr(network, "ssid", "")
            ssid = self.decode_ssid(ssid_raw)
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

        # ステップ3: 現在の表示対象帯域でフィルタリング（信号強度フィルター適用）
        target_band = self.band_var.get()
        signal_threshold = self.signal_filter_var.get()
        data = []
        unique_check = set()
        total_band_count = 0

        for key, value in self.wifi_cache.items():
            if value["band"] != target_band:
                continue

            # 重複チェック（同じSSID+チャンネルの組み合わせ）
            if key in unique_check:
                continue
            unique_check.add(key)

            total_band_count += 1

            # 信号強度フィルター適用
            if value["signal"] >= signal_threshold:
                data.append({
                    "channel": value["channel"],
                    "signal": value["signal"],
                    "ssid": value["ssid"],
                    "band": value["band"]
                })

        print(f"{target_band}帯の有効データ: {len(data)}/{total_band_count} 件（キャッシュ総数: {len(self.wifi_cache)}）")
        df = pd.DataFrame(data)
        self.root.after(0, lambda: self.update_graph(df, target_band, total_band_count))

    def _channel_axis(self, band):
        if band == "2.4GHz":
            return list(np_linspace(1, 14, 200)), list(range(1, 15)), (1, 14)
        return list(np_linspace(34, 179, 500)), list(range(34, 180, 8)), (34, 179)

    def _curve(self, x_axis, center_ch, peak_dbm, band, base=-100):
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

    def update_graph(self, df, band, total_count=0):
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

        # フィルター閾値に合わせてY軸の下限を動的に設定
        signal_threshold = self.signal_filter_var.get()
        y_min = signal_threshold - 5 if signal_threshold > -100 else -100
        y_min = max(y_min, -100)  # -100未満にはしない

        # グリッド設定（見やすいグレー）
        self.ax.grid(True, linestyle="--", alpha=0.5, color="#999999")
        self.ax.set_ylim(y_min, -20)
        self.ax.set_xlim(x_min, x_max)

        if df.empty:
            y_center = (y_min + (-20)) / 2
            self.ax.text((x_min+x_max)/2, y_center, "No Wi-Fi Found", ha="center", color="#333", fontsize=14)
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

            y_curve = self._curve(x_axis, row["channel"], row["signal"], band, base=y_min)

            z = 10 if is_connected else 5

            self.ax.fill_between(x_axis, y_curve, y_min, color=color, alpha=0.3, zorder=z)
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

        # フィルター件数表示を更新
        displayed = len(df)
        if total_count > 0 and total_count != displayed:
            self.filter_count_label.config(text=f"({displayed}/{total_count} 件表示中)", foreground="#D32F2F")
        elif total_count > 0:
            self.filter_count_label.config(text=f"({displayed} 件全表示)", foreground="gray")
        else:
            self.filter_count_label.config(text="")

        msg = f"{band}帯: {displayed} 件検出"
        self.log_message(msg)

def np_linspace(start, stop, num):
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]

if __name__ == "__main__":
    root = tk.Tk()
    app = WifiAnalyzerApp(root)
    root.mainloop()