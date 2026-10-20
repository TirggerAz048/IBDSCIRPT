import ast
import os

BASE = r'D:\project\IBDscript\IBDspider-PlanTwo'

files = [
    'gui/panels/hk_panel.py',
    'gui/panels/us_panel.py',
    'gui/panels/ipo_panel.py',
    'gui/panels/wechat_panel.py',
    'gui/panels/settings_panel.py',
    'gui/pages/home_page.py',
    'gui/pages/DeepSeek_Page.py',
    'workers/wechat_worker.py',
    'workers/wechat_client.py',
    'workers/ipo_utils.py',
    'workers/ipo_client.py',
    'workers/ipo_worker.py',
    'workers/ai/base_injector.py',
    'workers/ai/deepseek_injector.py',
    'workers/ai/ipo_injector.py',
]

result_dir = r'c:\Users\Administrator\WorkBuddy\2026-05-20-14-25-58'
out_path = os.path.join(result_dir, '_verify_result.txt')

results = []
for f in files:
    full = os.path.join(BASE, f)
    try:
        with open(full, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read())
        results.append(f"OK: {f}")
    except SyntaxError as e:
        results.append(f"FAIL: {f} -- {e}")
    except Exception as e:
        results.append(f"ERROR: {f} -- {e}")

summary = '\n'.join(results)
summary += f"\n\nTotal: {len(results)} files checked"

with open(out_path, 'w', encoding='utf-8') as out:
    out.write(summary)
