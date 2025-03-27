"""
    GameVault-Relocator Updater
    Copyright (C) 2025 ScriptedBits

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
"""
   ===========================================================================================
                          GameVault-Relocator Updater
   ===========================================================================================
	This script will allow you to move folders to a new drive or location and create a symlink
    from the source directory

    GitHub Repository: https://github.com/ScriptedBits/GameVault-Relocator
   
    Author: ScriptedBits
    License: GPL3

    For any support or issues, Please visit the github respository
    ==========================================================================================
"""
import os
import sys
import time
import shutil
import subprocess
import psutil

LOG_PATH = os.path.join(os.path.dirname(__file__), "updater.log")

def log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_PATH, "a") as f:
        f.write(f"{timestamp} {msg}\n")
    print(msg)

def wait_for_process_exit(target_exe, timeout=30):
    exe_name = os.path.basename(target_exe)
    log(f"Waiting for process {exe_name} to exit (timeout: {timeout}s)")

    for i in range(timeout):
        if not is_process_running(exe_name):
            log(f"Process {exe_name} has exited.")
            return True
        time.sleep(1)

    log("Timeout reached. Continuing anyway.")
    return False

def is_process_running(exe_name):
    for proc in psutil.process_iter(attrs=['name']):
        try:
            if proc.info['name'].lower() == exe_name.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def safely_replace_exe(new_exe, target_exe):
    try:
        if os.path.exists(target_exe):
            os.remove(target_exe)
            log(f"Deleted old executable: {target_exe}")
        shutil.move(new_exe, target_exe)
        log(f"Moved new executable into place: {target_exe}")
    except Exception as e:
        log(f"Error during replacement: {e}")
        sys.exit(1)

def relaunch_exe(target_exe):
    try:
        subprocess.Popen([target_exe], shell=False)
        log("Application relaunched.")
    except Exception as e:
        log(f"Failed to relaunch app: {e}")
        sys.exit(1)

def self_delete():
    # Only works for .py runs (won't work for frozen .exe)
    try:
        os.remove(sys.argv[0])
        log("Self-deleted updater script.")
    except Exception as e:
        log(f"Self-deletion failed: {e}")

def main():
    if len(sys.argv) < 3:
        log("Usage: updater.py <new_exe> <target_exe>")
        sys.exit(1)

    new_exe = sys.argv[1]
    target_exe = sys.argv[2]

    wait_for_process_exit(target_exe)
    safely_replace_exe(new_exe, target_exe)
    relaunch_exe(target_exe)

    # Optional: self-delete
    self_delete()
    sys.exit(0)

if __name__ == "__main__":
    main()
