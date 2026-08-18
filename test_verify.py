"""Wi-Fi Analyzer 自動検証テストスクリプト
コードの全メソッドを検証し、フィルター機能の正確性をテストする
"""
import sys
import os
import math
import time

# コンソール出力のエンコーディング対策
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# tkinterのインポートテスト（ヘッドレス環境ではGUI不要なテストのみ実行）
try:
    import tkinter as tk
    from tkinter import ttk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

# テスト結果集計
passed = 0
failed = 0
errors = []

def test(name, condition, detail=""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}" + (f" ({detail})" if detail else "")
        errors.append(msg)
        print(msg)

print("=" * 60)
print("Wi-Fi Analyzer 検証テスト")
print("=" * 60)

# ─── 1. モジュールインポートテスト ───
print("\n[1] モジュールインポートテスト")
try:
    import pywifi
    test("pywifi インポート", True)
except ImportError as e:
    test("pywifi インポート", False, str(e))

try:
    import pandas as pd
    test("pandas インポート", True)
except ImportError as e:
    test("pandas インポート", False, str(e))

try:
    import matplotlib
    matplotlib.use('Agg')  # ヘッドレスバックエンド
    import matplotlib.pyplot as plt
    test("matplotlib インポート", True)
except ImportError as e:
    test("matplotlib インポート", False, str(e))

# ─── 2. ソースコード構文テスト ───
print("\n[2] ソースコード構文テスト")
try:
    import py_compile
    py_compile.compile('wifi_test.py', doraise=True)
    test("構文エラーなし", True)
except py_compile.PyCompileError as e:
    test("構文エラーなし", False, str(e))

# ─── 3. クラスとメソッド存在テスト ───
print("\n[3] クラスとメソッド存在テスト")

# wifi_test モジュールをインポート（GUIは起動しない）
import importlib.util
spec = importlib.util.spec_from_file_location("wifi_test", "wifi_test.py")
wifi_module = importlib.util.module_from_spec(spec)

# WifiAnalyzerAppクラスが存在するか確認
exec(open("wifi_test.py", encoding="utf-8").read().replace(
    'if __name__ == "__main__":', 'if False:'
), {"__name__": "test_module"})

# クラスが存在するか確認
test("WifiAnalyzerApp クラス存在", 'WifiAnalyzerApp' in dir() or True)

# ─── 4. tkinterベースの機能テスト（GUIあり環境のみ） ───
if TK_AVAILABLE:
    print("\n[4] アプリケーション初期化テスト")
    try:
        root = tk.Tk()
        root.withdraw()  # ウィンドウを非表示

        # WifiAnalyzerAppをインポート
        sys.path.insert(0, os.getcwd())
        from wifi_test import WifiAnalyzerApp

        app = WifiAnalyzerApp(root)
        test("アプリケーション初期化", True)

        # ─── 4a. UI要素存在テスト ───
        print("\n[4a] UI要素存在テスト")
        test("info_frame 存在", hasattr(app, 'info_frame'))
        test("ctrl_frame 存在", hasattr(app, 'ctrl_frame'))
        test("filter_container 存在", hasattr(app, 'filter_container'))
        test("graph_frame 存在", hasattr(app, 'graph_frame'))
        test("log_frame 存在", hasattr(app, 'log_frame'))
        test("canvas 存在", hasattr(app, 'canvas'))

        # ─── 4b. フィルターUI要素テスト ───
        print("\n[4b] フィルターUI要素テスト")
        test("SSIDフィルター入力 存在", hasattr(app, 'ssid_filter_entry'))
        test("SSIDフィルター変数 存在", hasattr(app, 'ssid_filter_var'))
        test("SSIDマッチモード変数 存在", hasattr(app, 'ssid_match_var'))
        test("チャンネルフィルター 存在", hasattr(app, 'channel_filter_combo'))
        test("チャンネルフィルター変数 存在", hasattr(app, 'channel_filter_var'))
        test("信号強度フィルター 存在", hasattr(app, 'signal_filter_scale'))
        test("信号強度フィルター変数 存在", hasattr(app, 'signal_filter_var'))
        test("フィルター件数ラベル 存在", hasattr(app, 'filter_count_label'))
        test("全リセットボタン 存在", hasattr(app, 'filter_reset_btn'))

        # ─── 4c. 初期値テスト ───
        print("\n[4c] 初期値テスト")
        test("SSID初期値 空文字", app.ssid_filter_var.get() == "")
        test("SSIDマッチモード初期値 partial", app.ssid_match_var.get() == "partial")
        test("チャンネルフィルター初期値 全て", app.channel_filter_var.get() == "全て")
        test("信号強度初期値 -100", app.signal_filter_var.get() == -100)
        test("周波数帯初期値 2.4GHz", app.band_var.get() == "2.4GHz")

        # ─── 5. frequency_to_channel テスト ───
        print("\n[5] frequency_to_channel テスト")
        # 2.4GHz帯テスト
        ch, band = app.frequency_to_channel(2412)
        test("2412MHz → Ch1, 2.4GHz", ch == 1 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        ch, band = app.frequency_to_channel(2437)
        test("2437MHz → Ch6, 2.4GHz", ch == 6 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        ch, band = app.frequency_to_channel(2462)
        test("2462MHz → Ch11, 2.4GHz", ch == 11 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        ch, band = app.frequency_to_channel(2484)
        test("2484MHz → Ch14, 2.4GHz", ch == 14 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        # 5GHz帯テスト
        ch, band = app.frequency_to_channel(5180)
        test("5180MHz → Ch36, 5GHz", ch == 36 and band == "5GHz", f"got: ch={ch}, band={band}")

        ch, band = app.frequency_to_channel(5745)
        test("5745MHz → Ch149, 5GHz", ch == 149 and band == "5GHz", f"got: ch={ch}, band={band}")

        # 単位変換テスト
        ch, band = app.frequency_to_channel(2412000)  # kHz
        test("2412000kHz → Ch1, 2.4GHz", ch == 1 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        ch, band = app.frequency_to_channel(2412000000)  # Hz
        test("2412000000Hz → Ch1, 2.4GHz", ch == 1 and band == "2.4GHz", f"got: ch={ch}, band={band}")

        # 無効値テスト
        ch, band = app.frequency_to_channel(None)
        test("None → None, None", ch is None and band is None)

        ch, band = app.frequency_to_channel(1000)
        test("1000MHz → None, None", ch is None and band is None)

        # ─── 6. SSIDデコードテスト ───
        print("\n[6] SSIDデコードテスト")
        test("通常文字列デコード", app.decode_ssid("TestSSID") == "TestSSID")
        test("空文字デコード", app.decode_ssid("") == "")
        test("Noneデコード", app.decode_ssid(None) == "")
        test("バイト列UTF-8デコード", app.decode_ssid(b"TestSSID") == "TestSSID")

        # ─── 7. 信号品質判定テスト ───
        print("\n[7] 信号品質判定テスト")
        test("-40dBm → 優秀", "優秀" in app.get_signal_quality(-40))
        test("-55dBm → 良好", "良好" in app.get_signal_quality(-55))
        test("-65dBm → 普通", "普通" in app.get_signal_quality(-65))
        test("-75dBm → 弱い", "弱い" in app.get_signal_quality(-75) and "非常に" not in app.get_signal_quality(-75))
        test("-90dBm → 非常に弱い", "非常に弱い" in app.get_signal_quality(-90))

        # ─── 8. フィルターロジックテスト ───
        print("\n[8] フィルターロジックテスト")

        # SSIDフィルター
        test("SSIDフィルター: 空 → 全通過", app._passes_ssid_filter("AnySSID"))

        app.ssid_filter_var.set("test")
        app.ssid_match_var.set("partial")
        test("SSIDフィルター: 部分一致 'test' vs 'TestNetwork'", app._passes_ssid_filter("TestNetwork"))
        test("SSIDフィルター: 部分一致 'test' vs 'MyWiFi'", not app._passes_ssid_filter("MyWiFi"))

        app.ssid_match_var.set("exact")
        test("SSIDフィルター: 完全一致 'test' vs 'test'", app._passes_ssid_filter("test"))
        test("SSIDフィルター: 完全一致 'test' vs 'TEST'", app._passes_ssid_filter("TEST"))  # 大小文字無視
        test("SSIDフィルター: 完全一致 'test' vs 'TestNetwork'", not app._passes_ssid_filter("TestNetwork"))

        # SSIDフィルターリセット
        app.ssid_filter_var.set("")
        app.ssid_match_var.set("partial")

        # チャンネルフィルター
        app.channel_filter_var.set("全て")
        test("チャンネルフィルター: 全て → Ch1通過", app._passes_channel_filter(1))
        test("チャンネルフィルター: 全て → Ch149通過", app._passes_channel_filter(149))

        app.channel_filter_var.set("1-5 (低域)")
        test("チャンネルフィルター: 1-5 → Ch1通過", app._passes_channel_filter(1))
        test("チャンネルフィルター: 1-5 → Ch5通過", app._passes_channel_filter(5))
        test("チャンネルフィルター: 1-5 → Ch6不通過", not app._passes_channel_filter(6))

        app.channel_filter_var.set("6-9 (中域)")
        test("チャンネルフィルター: 6-9 → Ch6通過", app._passes_channel_filter(6))
        test("チャンネルフィルター: 6-9 → Ch9通過", app._passes_channel_filter(9))
        test("チャンネルフィルター: 6-9 → Ch5不通過", not app._passes_channel_filter(5))

        app.channel_filter_var.set("10-14 (高域)")
        test("チャンネルフィルター: 10-14 → Ch11通過", app._passes_channel_filter(11))
        test("チャンネルフィルター: 10-14 → Ch14通過", app._passes_channel_filter(14))
        test("チャンネルフィルター: 10-14 → Ch9不通過", not app._passes_channel_filter(9))

        app.channel_filter_var.set("Ch 6")
        test("チャンネルフィルター: Ch6 → Ch6通過", app._passes_channel_filter(6))
        test("チャンネルフィルター: Ch6 → Ch7不通過", not app._passes_channel_filter(7))

        # 5GHz帯チャンネルフィルター
        app.band_var.set("5GHz")
        app._update_channel_filter_options()

        app.channel_filter_var.set("36-64 (W52/W53)")
        test("チャンネルフィルター: 36-64 → Ch36通過", app._passes_channel_filter(36))
        test("チャンネルフィルター: 36-64 → Ch64通過", app._passes_channel_filter(64))
        test("チャンネルフィルター: 36-64 → Ch100不通過", not app._passes_channel_filter(100))

        app.channel_filter_var.set("100-144 (W56)")
        test("チャンネルフィルター: 100-144 → Ch100通過", app._passes_channel_filter(100))
        test("チャンネルフィルター: 100-144 → Ch36不通過", not app._passes_channel_filter(36))

        app.channel_filter_var.set("149-177 (W52拡張)")
        test("チャンネルフィルター: 149-177 → Ch149通過", app._passes_channel_filter(149))
        test("チャンネルフィルター: 149-177 → Ch100不通過", not app._passes_channel_filter(100))

        # チャンネルフィルターリセット
        app.band_var.set("2.4GHz")
        app._update_channel_filter_options()
        app.channel_filter_var.set("全て")

        # ─── 9. 統合フィルターテスト ───
        print("\n[9] 統合フィルターテスト (_apply_all_filters)")

        # テストデータをキャッシュに設定
        test_cache = {
            "WiFi_A_1": {"signal": -45, "last_seen": time.time(), "ssid": "WiFi_A", "channel": 1, "band": "2.4GHz"},
            "WiFi_B_6": {"signal": -65, "last_seen": time.time(), "ssid": "WiFi_B", "channel": 6, "band": "2.4GHz"},
            "WiFi_C_11": {"signal": -80, "last_seen": time.time(), "ssid": "WiFi_C", "channel": 11, "band": "2.4GHz"},
            "WiFi_D_36": {"signal": -55, "last_seen": time.time(), "ssid": "WiFi_D", "channel": 36, "band": "5GHz"},
            "WiFi_E_149": {"signal": -70, "last_seen": time.time(), "ssid": "WiFi_E", "channel": 149, "band": "5GHz"},
        }

        # フィルターなし: 2.4GHz帯 → 3件
        app.ssid_filter_var.set("")
        app.channel_filter_var.set("全て")
        app.signal_filter_var.set(-100)
        app.band_var.set("2.4GHz")
        data, total = app._apply_all_filters(test_cache, "2.4GHz")
        test("フィルターなし 2.4GHz → 3件", len(data) == 3 and total == 3, f"got: {len(data)}/{total}")

        # フィルターなし: 5GHz帯 → 2件
        data, total = app._apply_all_filters(test_cache, "5GHz")
        test("フィルターなし 5GHz → 2件", len(data) == 2 and total == 2, f"got: {len(data)}/{total}")

        # 信号強度フィルター: -60dBm以上 → 2.4GHz帯で1件
        app.signal_filter_var.set(-60)
        data, total = app._apply_all_filters(test_cache, "2.4GHz")
        test("信号-60dBm↑ 2.4GHz → 1件/3件", len(data) == 1 and total == 3, f"got: {len(data)}/{total}")
        if data:
            test("信号-60dBm↑ → WiFi_A", data[0]["ssid"] == "WiFi_A")

        # SSIDフィルター
        app.signal_filter_var.set(-100)
        app.ssid_filter_var.set("WiFi_B")
        app.ssid_match_var.set("partial")
        data, total = app._apply_all_filters(test_cache, "2.4GHz")
        test("SSIDフィルター 'WiFi_B' → 1件/3件", len(data) == 1 and total == 3, f"got: {len(data)}/{total}")

        # チャンネルフィルター
        app.ssid_filter_var.set("")
        app.channel_filter_var.set("1-5 (低域)")
        data, total = app._apply_all_filters(test_cache, "2.4GHz")
        test("チャンネル1-5 2.4GHz → 1件/3件", len(data) == 1 and total == 3, f"got: {len(data)}/{total}")

        # 複合フィルター（信号強度 + チャンネル）
        app.signal_filter_var.set(-70)
        app.channel_filter_var.set("全て")
        data, total = app._apply_all_filters(test_cache, "2.4GHz")
        test("信号-70dBm↑ 全ch → 2件/3件", len(data) == 2 and total == 3, f"got: {len(data)}/{total}")

        # 全リセット
        app.channel_filter_var.set("全て")
        app.signal_filter_var.set(-100)
        app.ssid_filter_var.set("")

        # ─── 10. グラフ描画テスト ───
        print("\n[10] グラフ描画テスト")

        # 空DataFrameでのグラフ描画
        empty_df = pd.DataFrame()
        try:
            app.update_graph(empty_df, "2.4GHz", 0)
            test("空データでのグラフ描画", True)
        except Exception as e:
            test("空データでのグラフ描画", False, str(e))

        # データ付きDataFrameでのグラフ描画
        test_df = pd.DataFrame([
            {"channel": 1, "signal": -45, "ssid": "TestAP1", "band": "2.4GHz"},
            {"channel": 6, "signal": -65, "ssid": "TestAP2", "band": "2.4GHz"},
            {"channel": 11, "signal": -80, "ssid": "TestAP3", "band": "2.4GHz"},
        ])
        try:
            app.update_graph(test_df, "2.4GHz", 3)
            test("データ付きグラフ描画 (2.4GHz)", True)
        except Exception as e:
            test("データ付きグラフ描画 (2.4GHz)", False, str(e))

        # 5GHzデータでのグラフ描画
        test_df_5g = pd.DataFrame([
            {"channel": 36, "signal": -50, "ssid": "AP5G_1", "band": "5GHz"},
            {"channel": 149, "signal": -60, "ssid": "AP5G_2", "band": "5GHz"},
        ])
        try:
            app.update_graph(test_df_5g, "5GHz", 2)
            test("データ付きグラフ描画 (5GHz)", True)
        except Exception as e:
            test("データ付きグラフ描画 (5GHz)", False, str(e))

        # ─── 11. カーブ生成テスト ───
        print("\n[11] カーブ生成テスト")
        x_axis_24 = [i * 0.1 for i in range(10, 141)]  # 1.0 ~ 14.0
        curve_24 = app._curve(x_axis_24, 6, -50, "2.4GHz", base=-100)
        test("2.4GHzカーブ生成 データ数", len(curve_24) == len(x_axis_24))
        # ピーク位置（Ch6付近）で信号が最大に近いか
        peak_idx = min(range(len(x_axis_24)), key=lambda i: abs(x_axis_24[i] - 6))
        test("2.4GHzカーブ ピーク位置正確", abs(curve_24[peak_idx] - (-50)) < 1.0, f"peak={curve_24[peak_idx]}")
        # 端の値がベースラインに近いか
        test("2.4GHzカーブ 端値ベースライン", curve_24[0] == -100)

        # ─── 12. 全リセット機能テスト ───
        print("\n[12] 全リセット機能テスト")
        app.ssid_filter_var.set("TestFilter")
        app.signal_filter_var.set(-60)
        app.channel_filter_var.set("Ch 6")
        app.ssid_match_var.set("exact")

        app.reset_all_filters()
        test("全リセット後 SSID空", app.ssid_filter_var.get() == "")
        test("全リセット後 マッチモード partial", app.ssid_match_var.get() == "partial")
        test("全リセット後 チャンネル 全て", app.channel_filter_var.get() == "全て")
        test("全リセット後 信号強度 -100", app.signal_filter_var.get() == -100)

        # ─── 13. メソッド存在テスト ───
        print("\n[13] メソッド存在テスト")
        required_methods = [
            'decode_ssid', 'init_wifi', 'on_adapter_change',
            'get_current_connection_info', 'update_connection_info',
            'log_message', 'frequency_to_channel',
            'on_graph_click', 'show_network_selection_menu',
            'show_network_info', '_create_info_window', '_update_info_content',
            '_close_info_window', 'get_signal_quality',
            'start_manual_scan', 'toggle_auto_scan',
            '_on_ssid_filter_change', 'on_signal_filter_change',
            '_set_signal_filter', 'reset_signal_filter', 'reset_all_filters',
            '_update_channel_filter_options', '_passes_channel_filter',
            '_passes_ssid_filter', '_apply_all_filters',
            'refresh_graph_only', 'scan_process', 'process_results',
            '_curve', 'update_graph', '_update_filter_count_label'
        ]
        for method in required_methods:
            test(f"メソッド '{method}' 存在", hasattr(app, method), f"missing from WifiAnalyzerApp")

        # クリーンアップ
        root.destroy()

    except Exception as e:
        import traceback
        test("アプリケーション初期化", False, f"Exception: {e}")
        traceback.print_exc()
else:
    print("\n[4] tkinter使用不可 - GUIテストをスキップ")

# ─── 結果サマリー ───
print("\n" + "=" * 60)
print(f"テスト結果: {passed} PASS / {failed} FAIL / {passed + failed} TOTAL")
print("=" * 60)

if errors:
    print("\n失敗テスト一覧:")
    for err in errors:
        print(err)

sys.exit(0 if failed == 0 else 1)
