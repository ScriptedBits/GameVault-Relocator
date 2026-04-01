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
import ctypes

LOG_PATH = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "updater.log")

def log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {msg}\n")
        print(msg)
    except:
        print(msg)

def is_admin():
    """Check if the current process has admin rights"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def restart_as_admin():
    """Restart the updater with administrator privileges"""
    if is_admin():
        return True
    
    try:
        script = sys.executable
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        sys.exit(0)  # Exit current non-admin instance
    except Exception as e:
        log(f"Failed to elevate to administrator: {e}")
        return False

def is_process_running(exe_name):
    exe_name = exe_name.lower()
    for proc in psutil.process_iter(attrs=['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == exe_name:
                return True
        except:
            continue
    return False

def wait_for_process_exit(target_exe, timeout=45):
    exe_name = os.path.basename(target_exe)
    log(f"Waiting for '{exe_name}' to close (up to {timeout} seconds)...")
    
    for i in range(timeout):
        if not is_process_running(exe_name):
            log("Main application has exited.")
            return True
        time.sleep(1)
    
    log("Warning: Timeout reached. Continuing anyway...")
    return False

def safely_replace_exe(new_exe, target_exe):
    try:
        if os.path.exists(target_exe):
            for attempt in range(4):
                try:
                    os.remove(target_exe)
                    log(f"Deleted old executable (attempt {attempt+1})")
                    break
                except Exception as e:
                    log(f"Delete attempt {attempt+1} failed: {e}")
                    time.sleep(1.5)
            else:
                log("ERROR: Could not delete old executable.")
                return False

        shutil.move(new_exe, target_exe)
        log(f"Successfully installed new version: {target_exe}")
        return True
    except Exception as e:
        log(f"CRITICAL ERROR during file replacement: {e}")
        return False

def relaunch_exe(target_exe):
    try:
        log(f"Relaunching application: {target_exe}")
        subprocess.Popen([target_exe], shell=False, close_fds=True)
        log("Application relaunched successfully.")
        return True
    except Exception as e:
        log(f"Failed to relaunch: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        log("ERROR: Incorrect usage.")
        print("Usage: updater.exe <new_version.exe> <current_app.exe>")
        time.sleep(6)
        sys.exit(1)

    new_exe = sys.argv[1]
    target_exe = sys.argv[2]

    log("=" * 70)
    log("GameVault-Relocator Updater Started")
    log(f"New version : {new_exe}")
    log(f"Target      : {target_exe}")
    log("=" * 70)

    if not os.path.exists(new_exe):
        log(f"ERROR: New executable not found at: {new_exe}")
        time.sleep(5)
        sys.exit(1)

    # Request admin rights if not already elevated
    if not restart_as_admin():
        log("Failed to get administrator privileges. Update may fail.")
        time.sleep(4)

    wait_for_process_exit(target_exe, timeout=50)

    if not safely_replace_exe(new_exe, target_exe):
        log("Update failed during replacement phase.")
        time.sleep(6)
        sys.exit(1)

    if relaunch_exe(target_exe):
        log("Update completed successfully!")
    else:
        log("Update completed, but failed to relaunch the application.")

    time.sleep(3)
    sys.exit(0)


if __name__ == "__main__":
    main()