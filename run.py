#!/usr/bin/env python3
"""
Crow Runner - Self-healing wrapper
Backs up before runs, restores on crash/stall
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).parent
BACKUP_DIR = WORKSPACE / "backup"
HEARTBEAT_FILE = WORKSPACE / ".heartbeat"
CRITICAL_FILES = ["main.py", "system_instructions.txt", "conversation.json", "conversation_full.json"]

# Stall detection: if no heartbeat for this many seconds, consider it stalled
STALL_TIMEOUT = 120  # 2 minutes


class C:
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.CYAN}[{ts}] [Runner]{C.RESET} {msg}")


def backup():
    """Backup critical files."""
    BACKUP_DIR.mkdir(exist_ok=True)
    for filename in CRITICAL_FILES:
        src = WORKSPACE / filename
        if src.exists():
            dst = BACKUP_DIR / filename
            shutil.copy2(src, dst)
    log(f"{C.GREEN}Backup created{C.RESET}")


def restore():
    """Restore from backup."""
    if not BACKUP_DIR.exists():
        log(f"{C.RED}No backup to restore!{C.RESET}")
        return False

    for filename in CRITICAL_FILES:
        src = BACKUP_DIR / filename
        if src.exists():
            dst = WORKSPACE / filename
            shutil.copy2(src, dst)
    log(f"{C.YELLOW}Restored from backup{C.RESET}")
    return True


def check_heartbeat():
    """Check if heartbeat is recent."""
    if not HEARTBEAT_FILE.exists():
        return True  # No heartbeat yet, give it time

    age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    return age < STALL_TIMEOUT


def run_crow():
    """Run main.py and monitor for crashes/stalls."""
    # Clear old heartbeat
    if HEARTBEAT_FILE.exists():
        HEARTBEAT_FILE.unlink()

    proc = subprocess.Popen(
        [sys.executable, WORKSPACE / "main.py"] + sys.argv[1:],
        cwd=WORKSPACE
    )

    # Monitor process
    while proc.poll() is None:
        time.sleep(5)
        if not check_heartbeat():
            log(f"{C.RED}Stall detected! Killing process...{C.RESET}")
            proc.kill()
            return "stall"

    exit_code = proc.returncode
    if exit_code == 0:
        return "clean"
    elif exit_code == 42:  # Special code for intentional restart
        return "restart"
    else:
        return "crash"


def main():
    log(f"{C.BOLD}Crow Runner starting{C.RESET}")

    crash_count = 0
    max_crashes = 3

    while True:
        # Backup before run
        backup()

        log("Starting Crow...")
        result = run_crow()

        if result == "clean":
            log(f"{C.GREEN}Crow exited cleanly{C.RESET}")
            break

        elif result == "restart":
            log(f"{C.YELLOW}Crow requested restart{C.RESET}")
            crash_count = 0  # Reset crash count on intentional restart
            continue

        elif result in ("crash", "stall"):
            crash_count += 1
            log(f"{C.RED}Crow {result}ed! (attempt {crash_count}/{max_crashes}){C.RESET}")

            if crash_count >= max_crashes:
                log(f"{C.RED}Too many crashes. Restoring backup and stopping.{C.RESET}")
                restore()
                break

            log("Restoring backup and retrying...")
            restore()
            time.sleep(2)


if __name__ == "__main__":
    main()
