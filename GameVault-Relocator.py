"""
    GameVault-Relocator
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
                          GameVault-Relocator
   ===========================================================================================
    This script will allow you to move folders to a new drive or location and create a symlink
    from the source directory

    GitHub Repository: https://github.com/ScriptedBits/GameVault-Relocator
   
    Author: ScriptedBits
    License: GPL3

    For any support or issues, Please visit the github respository
    ==========================================================================================
"""

import sys
import os
import re
import shutil
import ctypes
import subprocess
import time
import platform
import logging
import requests
import tempfile
import traceback
from packaging import version
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, 
    QMessageBox, QCheckBox, QProgressBar, QComboBox, QTextEdit, QSizePolicy, QDialog, QProgressDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QGuiApplication

if platform.system() == "Windows":
    import win32file

APP_VERSION = "3.0.6"

def check_for_updates():
    try:
        logging.info("Checking for updates...")
        logging.info(f"Current version: {APP_VERSION}")
        api_url = "https://api.github.com/repos/ScriptedBits/GameVault-Relocator/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()

        release_data = response.json()
        latest_version = release_data["tag_name"].lstrip("v")
        release_date_str = release_data["published_at"]
        release_date = datetime.strptime(release_date_str, "%Y-%m-%dT%H:%M:%SZ")

        asset_url = None
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe"):
                asset_url = asset["browser_download_url"]
                break

        logging.info(f"Latest GitHub release version: {latest_version}")

        if version.parse(latest_version) > version.parse(APP_VERSION) and asset_url:
            logging.info(f"Update available: {APP_VERSION} → {latest_version}")
            if getattr(sys, 'frozen', False):
                app_version_date = datetime.fromtimestamp(os.path.getmtime(sys.executable))
            else:
                app_version_date = datetime.fromtimestamp(os.path.getmtime(__file__))
            days_between = (release_date - app_version_date).days

            reply = QMessageBox.question(
                None,
                "Update Available",
                f"A new version of GameVault-Relocator is available!\n\n"
                f"Current version: {APP_VERSION}\n"
                f"Latest version: {latest_version}\n"
                f"Released {days_between} days after your current version.\n\n"
                "Would you like to download and install the update now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                temp_dir = tempfile.gettempdir()
                new_exe_path = os.path.join(temp_dir, f"GameVault-Relocator-{latest_version}.exe")
                logging.info(f"Downloading update to temp path: {new_exe_path}")
                logging.info(f"Downloading from: {asset_url}")

                response = requests.get(asset_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                block_size = 1024 * 1024

                progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100)
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setWindowTitle("Updating GameVault-Relocator")
                progress_dialog.setMinimumWidth(400)
                progress_dialog.setAutoClose(True)
                progress_dialog.show()

                downloaded = 0
                with open(new_exe_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            percent = int(downloaded * 100 / total_size)
                            progress_dialog.setValue(percent)
                            QApplication.processEvents()
                            if progress_dialog.wasCanceled():
                                logging.info("User cancelled update download.")
                                QMessageBox.information(None, "Update Cancelled", "The update has been cancelled.")
                                return

                logging.info("Download complete. Launching updater script.")
                run_updater_script(new_exe_path)

        elif not asset_url:
            logging.warning("Update found, but no .exe asset available.")
            QMessageBox.warning(None, "Update Check", "A new version is available but no .exe was found.")
        else:
            logging.info("No update available.")

    except requests.RequestException as e:
        logging.error(f"Update check failed: {e}")
        QMessageBox.warning(None, "Update Check Failed", f"An error occurred while checking for updates:\n{e}")
    except Exception as e:
        logging.exception("Unexpected error during update check.")
        QMessageBox.critical(None, "Update Error", f"Unexpected error:\n{str(e)}")


def download_and_replace_exe(asset_url, latest_version, parent=None):
    try:
        temp_dir = tempfile.gettempdir()
        new_exe_path = os.path.join(temp_dir, f"GameVault-Relocator-{latest_version}.exe")
        logging.info(f"Downloading update to: {new_exe_path}")

        response = requests.get(asset_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024

        progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100, parent)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setWindowTitle("Updating GameVault-Relocator")
        progress_dialog.setMinimumWidth(400)
        progress_dialog.show()

        downloaded = 0
        with open(new_exe_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = int((downloaded * 100) / total_size) if total_size > 0 else 0
                    progress_dialog.setValue(percent)
                    QApplication.processEvents()
                    if progress_dialog.wasCanceled():
                        logging.info("User cancelled update download.")
                        QMessageBox.information(parent, "Update Cancelled", "The update has been cancelled.")
                        return

        logging.info("Download complete. Launching updater...")
        
        # Small delay before launching updater
        QTimer.singleShot(300, lambda: run_updater_script(new_exe_path))
        QApplication.quit()

    except Exception as e:
        logging.error(f"Download or install failed: {e}")
        QMessageBox.warning(parent, "Update Failed", f"Failed to download or install the update:\n{e}")

def run_updater_script(new_exe_path):
    current_exe = sys.executable
    updater_filename = "updater.exe"
    temp_dir = tempfile.gettempdir()
    extracted_updater_path = os.path.join(temp_dir, updater_filename)

    try:
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        bundled_updater_path = os.path.join(bundle_dir, updater_filename)

        if not os.path.exists(bundled_updater_path):
            raise FileNotFoundError(f"Missing bundled updater: {bundled_updater_path}")

        # Copy updater to temp directory
        shutil.copyfile(bundled_updater_path, extracted_updater_path)
        logging.info(f"Copied updater to: {extracted_updater_path}")

        # Launch updater with admin rights (it will request UAC if needed)
        log_msg = f"Launching updater with: {new_exe_path} -> {current_exe}"
        logging.info(log_msg)

        subprocess.Popen(
            [extracted_updater_path, new_exe_path, current_exe],
            shell=False,
            close_fds=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if IS_WINDOWS else 0
        )

        logging.info("Updater launched successfully. Exiting main application.")
        sys.exit(0)

    except Exception as e:
        logging.exception("Failed to launch updater.")
        QMessageBox.critical(
            None, 
            "Update Error", 
            f"Could not launch the updater:\n\n{str(e)}\n\n"
            "Please make sure updater.exe is included in the build."
        )

LOG_FILE = "GameVault-Relocator.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"


def is_admin():
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.error(f"Error checking admin privileges: {e}")
            return False
    else:
        return os.geteuid() == 0


if not is_admin():
    try:
        if IS_WINDOWS:
            script = sys.executable
            params = " ".join(f'"{arg}"' for arg in sys.argv)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        else:
            script = sys.argv[0]
            params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
            subprocess.run(["sudo", sys.executable, script] + sys.argv[1:], check=True)

    except Exception as e:
        sys.exit(f"Failed to elevate to admin/root: {str(e)}")

    sys.exit()


def get_robocopy_thread_count():
    try:
        return min(os.cpu_count() or 4, 32)
    except:
        return 4


def get_available_drives(exclude_scan=False):
    drives = [] if exclude_scan else ["Scan drive"]
    
    if IS_WINDOWS:
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:/"
            try:
                drive_type = win32file.GetDriveType(drive)
                if os.path.exists(drive):
                    if drive_type == win32file.DRIVE_REMOTE:
                        drives.append(f"{drive} (Network)")
                    elif drive_type == win32file.DRIVE_FIXED:
                        drives.append(drive)
                    else:
                        drives.append(drive)
            except Exception as e:
                logging.warning(f"Skipping drive {drive}: {e}")
    else:
        try:
            import psutil
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                if os.path.ismount(p.mountpoint) and p.fstype:
                    drives.append(p.mountpoint)
        except Exception as e:
            logging.warning(f"Fallback: Could not list drives with psutil: {e}")
            for base in ["/mnt", "/media", "/Volumes"]:
                if os.path.exists(base):
                    for item in os.listdir(base):
                        full_path = os.path.join(base, item)
                        if os.path.ismount(full_path):
                            drives.append(full_path)
    return drives


class MoveThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    progress_summary = pyqtSignal(str)

    def __init__(self, source, destination, use_robocopy, preview_mode=False):
        super().__init__()
        self.source = source
        self.destination = destination
        self.use_robocopy = use_robocopy
        self.preview_mode = preview_mode
        self._stop_requested = False
        self.robocopy_process = None
        self.rsync_process = None

    def count_total_files(self, path):
        total_files = sum(len(files) for _, _, files in os.walk(path))
        return total_files

    def move_with_retries(self, src, dest, retries=5, delay=2):
        for attempt in range(1, retries + 1):
            try:
                shutil.move(src, dest)
                logging.info(f"Moved: {src} -> {dest}")
                return True
            except PermissionError:
                logging.warning(f"Attempt {attempt}: File in use - {src}")
                time.sleep(delay)
            except Exception as e:
                logging.error(f"Error moving file {src}: {e}")
                return False
        return False

    def remove_empty_dirs(self, path, retries=3, delay=2):
        for attempt in range(1, retries + 1):
            try:
                for root, dirs, _ in os.walk(path, topdown=False):
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            logging.info(f"Removed empty dir: {dir_path}")
                return True
            except Exception as e:
                logging.warning(f"Attempt {attempt}: Failed to remove empty dirs in {path}: {e}")
                time.sleep(delay)
        logging.error(f"Final attempt failed: Could not remove {path}")
        return False

    def run(self):
        try:
            total_files = self.count_total_files(self.source)
            if total_files == 0:
                self.progress.emit(100)
                self.finished.emit("No files found in source directory.")
                return

            moved_files = 0
            start_time = time.time()
            log_file = None

            if getattr(sys, 'frozen', False):
                log_dir = os.path.dirname(sys.executable)
            else:
                log_dir = os.path.abspath(".")

            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            if self.preview_mode:
                total_size_gb = sum(
                    os.path.getsize(os.path.join(root, f)) 
                    for root, _, files in os.walk(self.source) 
                    for f in files
                ) / (1024 ** 3)
                
                self.finished.emit(
                    f"[Preview Mode] Would move {total_files} files from:\n"
                    f"{self.source}\nto\n{self.destination}\n"
                    f"Total size: {total_size_gb:.2f} GB"
                )
                return

            # ====================== ROBOCOPY (Primary Path) ======================
            if IS_WINDOWS and self.use_robocopy:
                log_file = os.path.join(log_dir, f"robocopy_{timestamp}.log")
                thread_count = get_robocopy_thread_count()
                logging.info(f"Using Robocopy with {thread_count} threads")

                robocopy_command = [
                    "robocopy", self.source, self.destination,
                    "/E", "/MOVE", "/NP", "/R:3", "/W:2",
                    f"/MT:{thread_count}",
                    f"/LOG:{log_file}"
                ]

                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                self.robocopy_process = subprocess.Popen(
                    robocopy_command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=si
                )

                time.sleep(1.0)  # Give Robocopy time to start writing

                while self.robocopy_process.poll() is None:
                    if self._stop_requested:
                        self.robocopy_process.terminate()
                        self.finished.emit("Transfer canceled by user.")
                        return

                    moved_files = 0
                    try:
                        if os.path.exists(log_file):
                            with open(log_file, "r", encoding="mbcs", errors="replace") as f:
                                content = f.read()
                                # Robust counting: count every "New File" occurrence
                                moved_files = content.count("New File")
                    except Exception:
                        pass

                    progress = min(99, int((moved_files / total_files) * 100)) if total_files > 0 else 0
                    self.progress.emit(progress)
                    self.progress_summary.emit(f"{moved_files}/{total_files} files moved... (Robocopy)")

                    time.sleep(0.7)

                self.robocopy_process.wait()

                if self._stop_requested:
                    self.finished.emit("Transfer canceled by user.")
                    return

                # Read final count from the completed log (most accurate)
                try:
                    if os.path.exists(log_file):
                        with open(log_file, "r", encoding="mbcs", errors="replace") as f:
                            content = f.read()
                            moved_files = content.count("New File")
                except Exception:
                    pass

                # Clean up source if empty
                if os.path.exists(self.source):
                    try:
                        remaining = any(os.path.isfile(os.path.join(r, f)) 
                                        for r, _, fs in os.walk(self.source) for f in fs)
                        if not remaining:
                            os.system(f'rmdir /S /Q "{self.source}"')
                            logging.info(f"Source directory removed: {self.source}")
                    except Exception as e:
                        logging.warning(f"Could not remove source: {e}")

            # ====================== NATIVE PYTHON MOVE (Fallback) ======================
            else:
                log_file = os.path.join(log_dir, f"move_{timestamp}.log")
                moved_files = 0
                total_bytes_moved = 0

                for root, dirs, files in os.walk(self.source, topdown=False):
                    if self._stop_requested:
                        self.finished.emit("Transfer canceled by user.")
                        return

                    for file in files:
                        src_file = os.path.join(root, file)
                        dest_file = src_file.replace(self.source, self.destination, 1)
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                        try:
                            file_size = os.path.getsize(src_file) if os.path.exists(src_file) else 0
                            if self.move_with_retries(src_file, dest_file):
                                moved_files += 1
                                total_bytes_moved += file_size
                            else:
                                logging.warning(f"Failed to move: {src_file}")
                        except Exception as e:
                            logging.error(f"Error moving {src_file}: {e}")

                        progress = int((moved_files / total_files) * 100)
                        self.progress_summary.emit(f"{moved_files}/{total_files} files moved")
                        self.progress.emit(progress)

                if not self.remove_empty_dirs(self.source):
                    logging.error(f"Could not remove empty directories in {self.source}")

            # ====================== FINAL SUMMARY ======================
            elapsed_time = time.time() - start_time

            # Calculate accurate total size from destination
            try:
                total_bytes_moved = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(self.destination)
                    for f in files
                )
            except Exception:
                total_bytes_moved = 0

            moved_gb = total_bytes_moved / (1024 ** 3)

            self.progress.emit(100)

            self.finished.emit(
                f"Move completed successfully to:\n{self.destination}\n\n"
                f"Files moved : {moved_files} / {total_files}\n"
                f"Total size  : {moved_gb:.2f} GB\n"
                f"Time taken  : {elapsed_time:.2f} seconds\n"
                f"Log file    : {log_file}"
            )

        except Exception as e:
            logging.exception("Error in MoveThread.run()")
            self.finished.emit(f"Unexpected error during transfer:\n{str(e)}")
            
    def stop(self):
        self._stop_requested = True
        if self.robocopy_process and self.robocopy_process.poll() is None:
            self.robocopy_process.terminate()
        if self.rsync_process and self.rsync_process.poll() is None:
            self.rsync_process.terminate()


class SymlinkCheckerThread(QThread):
    progress = pyqtSignal(str)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.excluded_dirs = {
            # Legacy / compatibility junctions
            'documents and settings', 'all users', 'default user',
            'application data', 'local settings', 'my documents',
            'nethood', 'printhood', 'recent', 'sendto', 'start menu', 'templates',

            # AppData legacy redirects
            'appdata/local/application data',
            'appdata/local/history',
            'appdata/local/temporary internet files',
            'appdata/local/microsoft/windows/inetcache',
            'appdata/local/microsoft/windows/inetcookies',

            # Shell folder redirects
            'my music', 'my pictures', 'my videos',

            # ProgramData public folders
            'programdata/desktop',
            'programdata/documents',

            # Internet Explorer / legacy
            'cookies',
            'content.ie5',
            'low/content.ie5',

            # Office / ClickToRun
            'clicktorun',
            'vfs/programfiles',
            'vfs/programfilescommonx64',
            'vfs/programfilesx86',
            'appvisvsubsystems',
            'c2r32.dll',
            'c2r64.dll',

            # NVIDIA
            'nvcontainer/plugins',

            # System protected
            '$recycle.bin',
            'system volume information',

            # WindowsApps
            'windowsapps',

            # Unix-like
            'proc', 'sys', 'dev', 'tmp',

            # New additions for remaining noise
            'nethood',
            'printhood',
            
            'temporary internet files',
            'inetcache',  # broader catch for INetCache redirects
        }
    def run(self):
        try:
            output_lines = []
            logging.info(f"Starting symlink scan on path: {self.path}")

            if IS_WINDOWS:
                path_clean = self.path.rstrip('\\/')
                path_quoted = f'"{path_clean}\\"'
                cmd = f'dir {path_quoted} /AL /S /B'
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )

                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue

                    # Normalize line: lowercase + forward slashes + no trailing slash
                    norm_line = line.lower().replace('\\', '/').rstrip('/')

                    # Normalize exclusions on-the-fly and check
                    if any(
                        excl.lower().replace('\\', '/') in norm_line
                        for excl in self.excluded_dirs
                    ):
                        continue

                    # Skip WindowsApps
                    if '/microsoft/windowsapps' in norm_line:
                        continue

                    # Build info
                    symlink_info = f"{line} → (processing error)"

                    try:
                        target = os.readlink(line)
                        if target.startswith(r"\\?\\") or target.startswith("\\\\?\\"):
                            target = target[4:]
                        symlink_info = f"{line} → {target}"
                    except ValueError:
                        symlink_info = f"{line} → (Windows junction or reparse point)"
                    except OSError as e:
                        symlink_info = f"{line} → (broken or inaccessible: {e})"
                    except Exception as e:
                        symlink_info = f"{line} → (unexpected error: {str(e)})"

                    # Deduplicate + log + update UI **only if new**
                    if symlink_info not in output_lines:
                        output_lines.append(symlink_info)
                        logging.info(f"Found symlink: {symlink_info}")
                        self.progress.emit("\n".join(output_lines))

                stderr = process.stderr.read()
                process.wait()

                if process.returncode != 0:
                    stderr_clean = stderr.strip()
                    if "File Not Found" in stderr_clean or not stderr_clean:
                        logging.info("No symlinks or junctions found on this drive.")
                        self.finished.emit("No symlinks or junctions found.")
                        return
                    else:
                        logging.error(f"Symlink scan error (exit code {process.returncode}): {stderr_clean}")
                        self.finished.emit(f"Error scanning symlinks:\n\n{stderr_clean}")
                        return

            # Fallback
            if output_lines:
                result = "\n".join(output_lines) or "No symlinks or junctions found."
                self.finished.emit(result)
                return

            logging.info("No results from system command — falling back to Python os.walk scan")
            for root, dirs, files in os.walk(self.path, followlinks=False, topdown=True):
                if any(excluded_dir.lower() in root.lower() for excluded_dir in self.excluded_dirs):
                    continue

            result = "\n".join(output_lines) or "No symlinks or junctions found."
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"Unexpected error in symlink checker: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.finished.emit(f"Error during scan:\n{str(e)}")

class SymlinkMoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.base_symlink_instruction = (
            "Select a drive/folder and click <b>Check for Symlinks</b> to scan."
        )
        self.transfer_canceled = False
        self.source_path = None
        self.destination_path = None

        self.setWindowTitle(f"GameVault-Relocator v{APP_VERSION}")
        self.setGeometry(100, 100, 780, 700)   # Slightly taller to fit scanner comfortably
        self.center_window()

        self.setStyleSheet(self.get_dark_theme())
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ==================== PATH SELECTION ====================
        paths_group = QVBoxLayout()
        paths_group.setSpacing(8)

        self.source_label = QLabel("Source Directory: <span style='color:#888;'>Not Selected</span>")
        self.destination_label = QLabel("Destination: <span style='color:#888;'>Not Selected</span>")
        self.source_label.setWordWrap(True)
        self.destination_label.setWordWrap(True)

        paths_group.addWidget(self.source_label)
        paths_group.addWidget(self.destination_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.select_source_btn = QPushButton("📁 Select Source Directory")
        self.select_source_btn.setMinimumHeight(36)
        self.select_source_btn.clicked.connect(self.select_source)

        self.select_destination_btn = QPushButton("📁 Select Destination")
        self.select_destination_btn.setMinimumHeight(36)
        self.select_destination_btn.clicked.connect(self.select_destination)

        btn_layout.addWidget(self.select_source_btn)
        btn_layout.addWidget(self.select_destination_btn)

        paths_group.addLayout(btn_layout)
        main_layout.addLayout(paths_group)        # ← Add source + buttons here

        # ==================== DESTINATION OPTIONS ====================
        # Drive selector (shown when Preserve is checked)
        self.drive_label = QLabel("Destination Drive / Root:")
        main_layout.addWidget(self.drive_label)

        self.drive_combo = QComboBox()
        self.drive_combo.addItems(get_available_drives(exclude_scan=True))
        self.drive_combo.currentTextChanged.connect(self.on_drive_selected)
        main_layout.addWidget(self.drive_combo)

        # Preserve structure checkbox
        self.preserve_structure_cb = QCheckBox("Preserve original folder structure")
        self.preserve_structure_cb.setChecked(True)
        self.preserve_structure_cb.stateChanged.connect(self.toggle_destination_selector)
        main_layout.addWidget(self.preserve_structure_cb)

        # Spacer for visual separation
        main_layout.addSpacing(10)

        # ==================== OPTIONS ====================
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)

        if IS_WINDOWS:
            self.use_robocopy_checkbox = QCheckBox("Use Robocopy (faster on Windows)")
            self.use_robocopy_checkbox.setChecked(True)
            options_layout.addWidget(self.use_robocopy_checkbox)

        self.preview_checkbox = QCheckBox("Preview Only (Dry Run)")
        options_layout.addWidget(self.preview_checkbox)

        main_layout.addLayout(options_layout)

        # ==================== ACTION BUTTONS ====================
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.start_btn = QPushButton("🚀 Start Move + Create Symlink")
        self.start_btn.setMinimumHeight(42)
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; font-weight: bold; font-size: 11pt; }"
            "QPushButton:hover { background-color: #218838; }"
        )
        self.start_btn.clicked.connect(self.start_process)

        self.symlink_only_btn = QPushButton("🔗 Create Symlink Only")
        self.symlink_only_btn.setMinimumHeight(42)
        self.symlink_only_btn.setStyleSheet(
            "QPushButton { background-color: #1e3a8a; font-weight: bold; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        self.symlink_only_btn.clicked.connect(self.create_symlink_only)

        action_layout.addWidget(self.start_btn, stretch=1)
        action_layout.addWidget(self.symlink_only_btn, stretch=1)

        main_layout.addLayout(action_layout)

        self.stop_btn = QPushButton("⏹️ Cancel Transfer")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #dc3545; font-weight: bold; }"
            "QPushButton:hover { background-color: #c82333; }"
        )
        self.stop_btn.clicked.connect(self.cancel_transfer)
        self.stop_btn.hide()
        main_layout.addWidget(self.stop_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.progress_summary_label = QLabel("")
        self.progress_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_summary_label)

        # ==================== SYMLINK SCANNER SECTION ====================
        main_layout.addSpacing(15)
        main_layout.addWidget(QLabel("<b>Symlink Scanner</b>"))

        scan_layout = QHBoxLayout()
        self.drive_selection = QComboBox()
        self.drive_selection.addItems(get_available_drives(exclude_scan=False))
        scan_layout.addWidget(self.drive_selection, stretch=1)

        self.check_symlinks_btn = QPushButton("🔍 Check for Symlinks")
        self.check_symlinks_btn.setMinimumHeight(36)
        self.check_symlinks_btn.clicked.connect(self.start_symlink_check)
        scan_layout.addWidget(self.check_symlinks_btn)

        main_layout.addLayout(scan_layout)

        # === MISSING WIDGETS ADDED HERE ===
        self.symlink_instruction = QLabel(self.base_symlink_instruction)
        self.symlink_instruction.setTextFormat(Qt.TextFormat.RichText)
        self.symlink_instruction.setWordWrap(True)
        main_layout.addWidget(self.symlink_instruction)

        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)          # Indeterminate (spinning)
        self.scan_progress.setMaximumHeight(8)
        self.scan_progress.hide()
        main_layout.addWidget(self.scan_progress)

        self.symlink_results = QTextEdit()
        self.symlink_results.setReadOnly(True)
        self.symlink_results.setMaximumHeight(160)
        main_layout.addWidget(self.symlink_results)

        # ==================== BOTTOM BUTTONS ====================
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.info_btn = QPushButton("ℹ️ Info")
        self.help_btn = QPushButton("❓ Help")
        self.view_log_btn = QPushButton("📋 View Log")
        self.exit_btn = QPushButton("Exit")

        for btn in (self.info_btn, self.help_btn, self.view_log_btn, self.exit_btn):
            btn.setMinimumHeight(34)
            bottom_layout.addWidget(btn)

        self.info_btn.clicked.connect(self.show_info_popup)
        self.help_btn.clicked.connect(self.show_help_popup)
        self.view_log_btn.clicked.connect(self.show_log_viewer)
        self.exit_btn.clicked.connect(self.close)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        self.update_destination_label()
        self.toggle_destination_selector(Qt.CheckState.Checked.value)


    def toggle_destination_selector(self, state):
        preserve = (state == Qt.CheckState.Checked.value)

        # Show drive selector + label only when "Preserve" is checked
        self.drive_label.setVisible(preserve)
        self.drive_combo.setVisible(preserve)

        # Show "Select Destination" button only when Preserve is UNchecked
        self.select_destination_btn.setVisible(not preserve)

        if preserve:
            self.select_destination_btn.setText("Select Destination Root / Drive")
            # Auto-select first drive if nothing is set yet
            if self.drive_combo.count() > 0 and not getattr(self, 'destination_path', None):
                self.on_drive_selected(self.drive_combo.currentText())
        else:
            self.select_destination_btn.setText("Select Exact Destination Folder")
            self.destination_label.setText("Exact Destination Folder: Not Selected")

    def on_drive_selected(self, text):
        if self.preserve_structure_cb.isChecked():
            parts = text.split()
            drive_path = parts[0].rstrip("()")
            if drive_path.endswith(":"):
                drive_path += "/"
            self.destination_path = drive_path
            self.destination_label.setText(f"Destination Root: {drive_path}")


    def update_destination_label(self):
        if self.preserve_structure_cb.isChecked():
            self.destination_label.setText("Destination Root: Not Selected")
        else:
            self.destination_label.setText("Exact Destination Folder: Not Selected")


    def select_destination(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Exact Destination Folder",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            self.destination_path = folder
            self.destination_label.setText(f"Exact Destination: {folder}")


    def select_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if folder:
            self.source_path = folder
            self.source_label.setText(f"Source Directory: {folder}")


    def start_process(self):
        if not self.source_path or not self.destination_path:
            QMessageBox.warning(self, "Error", "Please select both source and destination.")
            return
        self.progress_summary_label.setText("")
        
        def get_folder_size(path):
            total = 0
            for root, _, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.exists(fp):
                        total += os.path.getsize(fp)
            return total

        def get_free_space(path):
            _, _, free = shutil.disk_usage(path)
            return free

        try:
            estimated_source_size = get_folder_size(self.source_path)
            destination_free = get_free_space(self.destination_path)

            if destination_free < estimated_source_size:
                source_gb = round(estimated_source_size / (1024 ** 3), 2)
                dest_free_gb = round(destination_free / (1024 ** 3), 2)
                QMessageBox.critical(
                    self,
                    "Insufficient Space",
                    f"The destination drive does not have enough free space.\n\n"
                    f"Estimated size of source: {source_gb} GB\n"
                    f"Available space on destination: {dest_free_gb} GB\n\n"
                    "Please free up space or choose another destination."
                )
                return
        except Exception as e:
            logging.error(f"Drive space check failed: {e}")
            QMessageBox.warning(self, "Drive Space Check Failed", f"Could not verify available space:\n{e}")
            return

        source_drive, source_rel = os.path.splitdrive(self.source_path)
        source_basename = os.path.basename(self.source_path)
        if self.preserve_structure_cb.isChecked():
            source_relative_path = source_rel.lstrip(os.sep)
            destination_final_path = os.path.join(self.destination_path, source_relative_path)
        else:
            destination_final_path = os.path.join(self.destination_path, source_basename)

        if not self.preview_checkbox.isChecked():
            os.makedirs(destination_final_path, exist_ok=True)

        self.progress_bar.setValue(0)
        self.worker = MoveThread(
            self.source_path,
            destination_final_path,
            self.use_robocopy_checkbox.isChecked() if IS_WINDOWS else False,
            self.preview_checkbox.isChecked()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_move_finished)
        self.worker.progress_summary.connect(self.progress_summary_label.setText)

        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.preview_checkbox.setEnabled(False)
        self.stop_btn.setText("Cancel Transfer")
        self.stop_btn.show()


    def on_move_finished(self, message):
        self.stop_btn.hide()
        self.stop_btn.setEnabled(True)
        self.preview_checkbox.setEnabled(True)
        self.stop_btn.setText("Cancel Transfer")
        self.progress_summary_label.setText("")
        self.start_btn.setEnabled(True)
        
        QMessageBox.information(self, "Process Complete", message)
        
        if self.transfer_canceled:
            logging.info("Transfer was canceled. Skipping symlink creation.")
            self.transfer_canceled = False
            return

        if self.preview_checkbox.isChecked():
            logging.info("Preview mode enabled — skipping symlink creation.")
            return

        source_drive, source_rel = os.path.splitdrive(self.source_path)
        source_basename = os.path.basename(self.source_path)
        if self.preserve_structure_cb.isChecked():
            source_relative_path = source_rel.lstrip(os.sep)
            destination_final_path = os.path.join(self.destination_path, source_relative_path)
        else:
            destination_final_path = os.path.join(self.destination_path, source_basename)

        logging.info(f"Attempting to create symlink: {self.source_path} -> {destination_final_path}")

        if os.path.exists(self.source_path):
            logging.info(f"Source directory still exists, attempting to remove: {self.source_path}")
            
            try:
                shutil.rmtree(self.source_path)
                logging.info(f"Successfully removed source directory: {self.source_path}")
            except Exception as e:
                logging.error(f"Failed to remove source directory: {e}")
                QMessageBox.critical(
                    self, "Error Removing Source Directory",
                    f"Could not remove the source directory:\n{self.source_path}\n\n"
                    "Please check if it's open in another program and try again."
                )
                return

        if IS_WINDOWS:
            symlink_command = f'mklink /D "{self.source_path}" "{destination_final_path}"'
        else:
            symlink_command = f'ln -s "{destination_final_path}" "{self.source_path}"'

        try:
            result = subprocess.run(symlink_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                logging.info(f"Symlink successfully created: {self.source_path} -> {destination_final_path}")
                if os.path.islink(self.source_path):
                    logging.info("Symlink verified.")
                else:
                    logging.warning("Symlink creation reported success but was not verified.")
                    
                QMessageBox.information(
                    self, "Symlink Created",
                    f"A symbolic link has been successfully created:\n\n"
                    f"Source: {self.source_path}\n"
                    f"Destination: {destination_final_path}"
                )
            else:
                logging.error(f"Symlink creation failed: {result.stderr}")
                QMessageBox.critical(
                    self, "Symlink Creation Failed",
                    f"Error creating symlink:\n\n{result.stderr}\n\n"
                    "Please check if you have the necessary permissions."
                )

        except Exception as e:
            logging.error(f"Exception creating symlink: {str(e)}")
            QMessageBox.critical(
                self, "Symlink Creation Error",
                f"An unexpected error occurred while creating the symlink:\n\n{str(e)}"
            )
    

    def create_symlink_only(self):
        if not self.source_path or not self.destination_path:
            QMessageBox.warning(self, "Missing Paths", "Please select both source and destination first.")
            return

        source_drive, source_rel = os.path.splitdrive(self.source_path)
        source_basename = os.path.basename(self.source_path)
        if self.preserve_structure_cb.isChecked():
            source_relative_path = source_rel.lstrip(os.sep)
            destination_final_path = os.path.join(self.destination_path, source_relative_path)
        else:
            destination_final_path = os.path.join(self.destination_path, source_basename)

        # Confirm the user has already moved their files and understands the source will be deleted
        reply = QMessageBox.warning(
            self,
            "Confirm Symlink Only",
            f"This will:\n\n"
            f"  1. DELETE the source folder:\n     {self.source_path}\n\n"
            f"  2. Create a symlink pointing to:\n     {destination_final_path}\n\n"
            f"Your files must already be at the destination before continuing.\n"
            f"If your files are NOT there yet, click No and use 'Start Move' instead.\n\n"
            f"Have you already moved your files to the destination?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            logging.info("User cancelled symlink-only operation at confirmation prompt.")
            return

        # Verify the destination exists and has content before touching the source
        if not os.path.isdir(destination_final_path) or not os.listdir(destination_final_path):
            QMessageBox.critical(
                self,
                "Destination Not Found or Empty",
                f"The destination folder does not exist or is empty:\n\n{destination_final_path}\n\n"
                f"Please move your files there first, then try again.\n"
                f"Your source folder has NOT been modified."
            )
            logging.warning(f"Symlink-only aborted — destination missing or empty: {destination_final_path}")
            return

        if os.path.exists(self.source_path):
            try:
                shutil.rmtree(self.source_path)
                logging.info(f"Removed original source: {self.source_path} before symlink-only operation.")
            except Exception as e:
                logging.error(f"Failed to remove source for symlink-only: {e}")
                QMessageBox.critical(self, "Error", f"Could not remove original source folder:\n{e}")
                return

        try:
            if IS_WINDOWS:
                cmd = f'mklink /D "{self.source_path}" "{destination_final_path}"'
            else:
                cmd = f'ln -s "{destination_final_path}" "{self.source_path}"'

            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                logging.info(f"Symlink (only) created: {self.source_path} → {destination_final_path}")
                QMessageBox.information(self, "Symlink Created", f"Symlink created:\n\n{self.source_path} → {destination_final_path}")
            else:
                raise RuntimeError(result.stderr)

        except Exception as e:
            logging.error(f"Symlink-only creation failed: {e}")
            QMessageBox.critical(self, "Symlink Error", f"Could not create symlink:\n{e}")


    def cancel_transfer(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.transfer_canceled = True
            self.worker._stop_requested = True
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Cancelling...")

            if hasattr(self.worker, 'robocopy_process') and self.worker.robocopy_process:
                try:
                    self.worker.robocopy_process.terminate()
                    logging.info("Robocopy process terminated by user.")
                except Exception as e:
                    logging.warning(f"Failed to terminate Robocopy: {e}")

    def start_symlink_check(self):
        selected_item = self.drive_selection.currentText()
        if selected_item == "Scan drive" or not selected_item:
            selected_path = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Symlinks")
            if not selected_path:
                self.symlink_results.setText("No folder selected.")
                return
        else:
            selected_path = selected_item

        self.symlink_results.setText("Scanning for symlinks...\nThis may take a while on large drives...")
        self.symlink_instruction.setText(
            self.base_symlink_instruction +
            f"<br><br><span style='color: #61afef;'>Scanning <b>{selected_path}</b>...</span>"
        )

        self.check_symlinks_btn.setEnabled(False)
        self.scan_progress.show()

        try:
            self.worker = SymlinkCheckerThread(selected_path)
            self.worker.progress.connect(self.symlink_results.setText)
            self.worker.finished.connect(self.on_symlink_check_finished)
            self.worker.start()
        except Exception as e:
            self.symlink_results.setText(f"Failed to start scan:\n{str(e)}")
            self.check_symlinks_btn.setEnabled(True)
            self.scan_progress.hide()

    def on_symlink_check_finished(self, result):
        selected_item = self.drive_selection.currentText()
        display_path = selected_item if selected_item != "Scan by Folder" else self.worker.path
        self.symlink_instruction.setText(
            self.base_symlink_instruction +
            f"<br><br><span style='color: #28a745; font-weight: bold;'>✔ Scan complete for {display_path}</span>"
        )

        self.symlink_results.setText(result)
        self.scan_progress.hide()
        self.check_symlinks_btn.setEnabled(True)


    def show_help_popup(self):
        help_text = """
            <h2 style='color: #61afef;'>How to Use GameVault-Relocator</h2>
            <ol style='color: white; font-size: 11pt;'>
            <li><b>Select Source Directory:</b><br>Pick the folder you want to move and create a symlink for.</li><br>
            <li><b>Select Destination:</b><br>Choose a root drive/folder when "Preserve source folder structure" is checked (default), or select the exact target folder when unchecked.</li><br>
            <li><b>Choose 'Start Move - Create Symlink':</b><br>The app will move files and create a symbolic link at the original source location.</li><br>
            <li><b>Or use 'Create Symlink Only (No Move)':</b><br>Use this if you already moved the files manually and just want to link them back.</li><br>
            <li><b>Check for Symlinks:</b><br>Select a drive and click 'Check for Symlinks' to view all current symbolic links.</li><br>
            <li><b>View Logs:</b><br>Click 'View Log' to see all actions taken and errors (if any).</li><br>
            </ol>
            <hr style='border: 1px solid #61afef; margin: 10px 0;'>
            <h3 style='color: #00ffff;'>🛠 To Update on Linux / macOS</h3>
            <ol start="1" style='color: white; font-size: 11pt;'>
            <li><b>Make Updater Executable:</b><br><code>chmod +x update.sh</code></li><br>
            <li><b>Run the Updater:</b><br><code>./update.sh /tmp/GameVault-Relocator-v2.1.3 /usr/local/bin/GameVault-Relocator</code></li><br>
            </ol>
            <p style='color:#98c379;'>💡 Tip: This tool requires administrator rights to create symlinks on Windows.</p>
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("Help & Examples")
        dialog.resize(750, 550)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_text)
        text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(text_edit)

        ok_button = QPushButton("Close")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.setLayout(layout)
        dialog.exec()

    def show_info_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About GameVault-Relocator")
        dialog.setFixedSize(850, 550)

        def get_resource_path(filename):
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, filename)
            return os.path.join(os.path.abspath("."), filename)

        background_path = get_resource_path("background.jpg")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        bg_label = QLabel(dialog)
        pixmap = QPixmap(background_path).scaled(
            dialog.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
        )
        bg_label.setPixmap(pixmap)
        bg_label.setGeometry(0, 0, dialog.width(), dialog.height())
        bg_label.lower()

        overlay = QWidget(dialog)
        overlay.setGeometry(0, 0, dialog.width(), dialog.height())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);")

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(40, 40, 40, 40)
        overlay_layout.setSpacing(20)

        info_text = (
            f"<h2 style='color: #61afef;'>GameVault-Relocator v{APP_VERSION}</h2>"
            "<p><b style='color:#98c379;'>Created by:</b> ScriptedBits</p>"
            "<p style='color:white;'>GameVault-Relocator is a passion project designed to save time by automating moving folders "
            "to another storage device or drive and creating a symlink to the source drive.</p>"
            '<p style="color:#ffffff;"><b>Project URL:</b><br>'
            '<a href="https://github.com/ScriptedBits/GameVault-Relocator" style="color:#00ffff;">'
            "https://github.com/ScriptedBits/GameVault-Relocator</a></p>"
        )

        info_label = QLabel(info_text)
        info_label.setOpenExternalLinks(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11pt;")
        overlay_layout.addWidget(info_label)

        ok_button = QPushButton("OK")
        ok_button.setFixedSize(100, 30)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #00ffff;
                color: #000000;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #00b3b3;
            }
        """)
        ok_button.clicked.connect(dialog.accept)
        overlay_layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()


    def show_log_viewer(self):
        log_path = LOG_FILE
        if not os.path.exists(log_path):
            QMessageBox.warning(self, "Log Not Found", "The log file does not exist.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Log Viewer")
        dialog.resize(700, 500)

        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        with open(log_path, 'r', encoding='mbcs', errors='replace') as f:
            text_edit.setText(f.read())

        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()

        clear_button = QPushButton("Clear Log")
        clear_button.setFixedSize(100, 30)
        clear_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")

        close_button = QPushButton("Close")
        close_button.setFixedSize(100, 30)

        def clear_log():
            reply = QMessageBox.question(
                self,
                "Confirm Clear Log",
                "Are you sure you want to clear the log file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    open(log_path, 'w').close()
                    text_edit.setText("")
                    logging.info("Log file cleared by user.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not clear log file:\n{e}")

        clear_button.clicked.connect(clear_log)
        close_button.clicked.connect(dialog.accept)

        button_layout.addStretch()
        button_layout.addWidget(clear_button)
        button_layout.addSpacing(10)
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()


    def center_window(self):
        frame_geometry = self.frameGeometry()
        screen_center = QGuiApplication.primaryScreen().geometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())


    def get_dark_theme(self):
        return """
            QWidget { background-color: #282c34; color: #abb2bf; font-size: 12pt; }
            QLabel { color: #ffffff; font-weight: bold; }
            QPushButton { 
                background-color: #61afef; 
                color: black; 
                border-radius: 4px; 
                padding: 4px; 
                font-size: 10pt; 
                min-height: 24px; 
            }
            QPushButton:hover { background-color: #528bbf; }
            QProgressBar {
                border: 2px solid #3c4049;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                background-color: #3c4049;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                width: 20px;
            }
            QCheckBox, QComboBox, QTextEdit { 
                background-color: #3c4049; 
                color: #ffffff; 
                border: 1px solid #61afef; 
            }
        """


if __name__ == "__main__":
    logging.info("GameVault-Relocator starting up...")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SymlinkMoverApp()
    window.show()
    logging.info("GameVault-Relocator GUI initialized and ready.")
    check_for_updates()
    sys.exit(app.exec())