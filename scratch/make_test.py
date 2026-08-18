import os

code = """import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import tkinter as tk
    from tkinter import ttk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

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
print("Wi-Fi Analyzer Verification Test")
print("=" * 60)

print("\\n[1] Module Import Test")
try:
    import pywifi
    test("pywifi import", True)
except ImportError as e:
    test("pywifi import", False, str(e))

try:
    import pandas as pd
    test("pandas import", True)
except ImportError as e:
    test("pandas import", False, str(e))

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    test("matplotlib import", True)
except ImportError as e:
    test("matplotlib import", False, str(e))

print("\\n[2] Syntax Test")
try:
    import py_compile
    py_compile.compile('wifi_test.py', doraise=True)
    test("No Syntax Error", True)
except py_compile.PyCompileError as e:
    test("No Syntax Error", False, str(e))

print("\\n[3] Class Import Test")
sys.path.insert(0, os.getcwd())
try:
    from wifi_test import WifiAnalyzerApp
    test("WifiAnalyzerApp Class Import", True)
except ImportError as e:
    test("WifiAnalyzerApp Class Import", False, str(e))

if TK_AVAILABLE:
    print("\\n[4] Application Init Test")
    try:
        root = tk.Tk()
        root.withdraw()
        app = WifiAnalyzerApp(root)
        test("Application Init", True)

        print("\\n[4a] UI Elements Existence")
        test("info_frame exists", hasattr(app, 'info_frame'))
        test("ctrl_frame exists", hasattr(app, 'ctrl_frame'))
        test("filter_frame exists", hasattr(app, 'filter_frame'))
        test("graph_frame exists", hasattr(app, 'graph_frame'))
        test("log_frame exists", hasattr(app, 'log_frame'))
        test("canvas exists", hasattr(app, 'canvas'))

        print("\\n[4b] Filter UI Elements")
        test("signal_filter_scale exists", hasattr(app, 'signal_filter_scale'))
        test("signal_filter_var exists", hasattr(app, 'signal_filter_var'))
        test("filter_count_label exists", hasattr(app, 'filter_count_label'))
        test("filter_reset_btn exists", hasattr(app, 'filter_reset_btn'))

        print("\\n[5] frequency_to_channel Test")
        ch, band = app.frequency_to_channel(2412)
        test("2412MHz -> Ch1, 2.4GHz", ch == 1 and band == "2.4GHz")
        ch, band = app.frequency_to_channel(5180)
        test("5180MHz -> Ch36, 5GHz", ch == 36 and band == "5GHz")

        print("\\n[6] decode_ssid Test")
        test("Normal string decode", app.decode_ssid("TestSSID") == "TestSSID")
        test("Empty string decode", app.decode_ssid("") == "")
        test("None decode", app.decode_ssid(None) == "")

        print("\\n[7] Signal Filter Reset Test")
        app.signal_filter_var.set(-60)
        app.reset_signal_filter()
        test("After reset signal_filter_var is -100", app.signal_filter_var.get() == -100)

        print("\\n[8] Required Methods Existence")
        required_methods = [
            'decode_ssid', 'init_wifi', 'on_adapter_change',
            'get_current_connection_info', 'update_connection_info',
            'log_message', 'frequency_to_channel',
            'on_graph_click', 'show_network_selection_menu',
            'show_network_info', 'start_manual_scan', 'toggle_auto_scan',
            'on_signal_filter_change', 'reset_signal_filter', 'refresh_graph_only'
        ]
        for method in required_methods:
            test(f"Method {method} exists", hasattr(app, method))

        root.destroy()
    except Exception as e:
        test("Application Init", False, str(e))

print("\\n" + "=" * 60)
print(f"Test Results: {passed} PASS / {failed} FAIL / {passed + failed} TOTAL")
print("=" * 60)
"""

with open('test_verify.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Updated test_verify.py successfully")
