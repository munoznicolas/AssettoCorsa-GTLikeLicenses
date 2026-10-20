#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import time
import re
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from tools.testing.ac_launcher import generate_race_ini, LOG_TXT_PATH, RACE_INI_PATH, ALT_USER_DOCS_AC, DEFAULT_AC_ROOT

def sync_to_ac():
    print("[INFO] Syncing to AC...")
    subprocess.run([sys.executable, os.path.join(REPO_ROOT, "tools", "sync_to_ac.py")], check=True)

def run_test_and_record(test_path, ac_root, ai_level=95):
    with open(test_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    test_id = test_data["test_id"]
    
    # 1. Generate race.ini
    race_ini_str = generate_race_ini(
        test_data,
        ac_root=ac_root,
        ai_level=ai_level,
        ai_test_mode=True
    )
    
    target_race_paths = [
        RACE_INI_PATH,
        os.path.join(ALT_USER_DOCS_AC, "cfg", "race.ini"),
        os.path.join(ac_root, "cfg", "race.ini"),
    ]
    for rp in target_race_paths:
        try:
            os.makedirs(os.path.dirname(rp), exist_ok=True)
            with open(rp, "w", encoding="utf-8") as f:
                f.write(race_ini_str)
        except Exception:
            pass
            
    # clear logs
    for lp in [LOG_TXT_PATH, os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt")]:
        if os.path.isfile(lp):
            try: os.remove(lp)
            except: pass
            
    # spawn
    acs_exe_path = os.path.join(ac_root, "acs.exe")
    proc = subprocess.Popen([acs_exe_path], cwd=ac_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"[{test_id}] Launched. Waiting for completion...")
    
    final_time = None
    medal = None
    t_start = time.time()
    max_duration = 180.0
    
    try:
        proc.wait(timeout=max_duration)
    except subprocess.TimeoutExpired:
        pass
        
    # check log once process is done
    if os.path.isfile(LOG_TXT_PATH):
        try:
            with open(LOG_TXT_PATH, "r", encoding="utf-8", errors="replace") as lf:
                content = lf.read()
                
                m = re.search(r"Test completed: medal='([^']+)' \| Time=([\d\.]+)s", content)
                if m:
                    medal = m.group(1)
                    final_time = float(m.group(2))
                
                elif "Failure triggered: reason=" in content:
                    m2 = re.search(r"Failure triggered: reason='([^']+)'", content)
                    medal = "FAILED"
                    final_time = m2.group(1) if m2 else "Unknown failure"
        except Exception:
            pass

    if medal is None:
        medal = "TIMEOUT_OR_CRASH"
        final_time = "N/A"
        
    # terminate proc
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except:
        try: proc.kill()
        except: pass
        
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/f", "/im", "acs.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
        
    return final_time, medal

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=str, help="Tier to run")
    parser.add_argument("--test", type=str, help="Single test to run")
    parser.add_argument("--ai-level", type=int, default=95)
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT)
    args = parser.parse_args()
    
    sync_to_ac()
    
    if args.test:
        test_files = [args.test]
    elif args.tier:
        pattern = os.path.join(REPO_ROOT, "content", "tests", args.tier, "test_*.json")
        test_files = sorted(glob.glob(pattern))
    else:
        pattern = os.path.join(REPO_ROOT, "content", "tests", "*", "test_*.json")
        test_files = sorted(glob.glob(pattern))
        
    results = []
    
    print(f"\nRunning {len(test_files)} tests...\n")
    
    for path in test_files:
        test_id = os.path.basename(path).replace(".json", "").replace("test_", "")
        t, m = run_test_and_record(path, args.ac_root, args.ai_level)
        print(f"-> {test_id}: {m} ({t})")
        results.append((test_id, m, t))
        
    print("\n--- RESULTS ---")
    for r in results:
        print(f"{r[0]}: {r[1]} - {r[2]}")

if __name__ == '__main__':
    main()

