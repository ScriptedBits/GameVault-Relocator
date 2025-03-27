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
import pkgutil
import sys
import os
import shutil
import ctypes
import subprocess
import time
import platform
import logging
import requests
import json
import tempfile
import webbrowser
import win32file
import traceback
from packaging import version
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, 
    QMessageBox, QCheckBox, QProgressBar, QComboBox, QTextEdit, QSpacerItem, QSizePolicy, QDialog, QProgressDialog, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap

APP_VERSION = "2.1.3"

def check_for_updates():
    try:
        logging.info("Checking for updates...")
        api_url = "https://api.github.com/repos/ScriptedBits/GameVault-Relocator/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()

        release_data = response.json()
        latest_version = release_data["tag_name"].lstrip("v")
        release_date_str = release_data["published_at"]
        release_date = datetime.strptime(release_date_str, "%Y-%m-%dT%H:%M:%SZ")

        # Find .exe asset in release
        asset_url = None
        for asset in release_data.get("assets", []):
            if asset["name"].endswith(".exe"):
                asset_url = asset["browser_download_url"]
                break

        logging.info(f"Latest GitHub release version: {latest_version}")

        if version.parse(latest_version) > version.parse(APP_VERSION) and asset_url:
            logging.info(f"Update available: {APP_VERSION} → {latest_version}")
            app_version_date = datetime.strptime("2025-03-01", "%Y-%m-%d")  # Adjust if needed
            days_between = (release_date - app_version_date).days

            reply = QMessageBox.question(
                None,
                "Update Available",
                f"A new version of GameVault-Relocator is available!\n\n"
                f"Current version: {APP_VERSION}\n"
                f"Latest version: {latest_version}\n"
                f"Released {days_between} days after your current version.\n\n"
                "Would you like to download and install the update now?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                temp_dir = tempfile.gettempdir()
                new_exe_path = os.path.join(temp_dir, f"GameVault-Relocator-{latest_version}.exe")
                logging.info(f"Downloading update to temp path: {new_exe_path}")
                logging.info(f"Downloading from: {asset_url}")

                response = requests.get(asset_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                block_size = 1024 * 1024

                progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100)
                progress_dialog.setWindowModality(Qt.WindowModal)
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

                # Pass current PyInstaller temp folder path
                _mei_dir = getattr(sys, '_MEIPASS', None)
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
        logging.info(f"Downloading update to temp path: {new_exe_path}")
        logging.info(f"Downloading from: {asset_url}")

        response = requests.get(asset_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024 * 1024

        progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100, parent)
        progress_dialog.setWindowModality(Qt.WindowModal)
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
                        QMessageBox.information(parent, "Update Cancelled", "The update has been cancelled.")
                        return

        logging.info("Download complete. Launching updater script.")
        
        #QTimer.singleShot(100, lambda: run_updater_script(new_exe_path, _mei_dir))
        QTimer.singleShot(100, lambda: run_updater_script(new_exe_path))
        QApplication.quit()  # this will trigger the shutdown gracefully

    except Exception as e:
        logging.error(f"Download or install failed: {e}")
        QMessageBox.warning(parent, "Update Failed", f"Failed to download or install the update:\n{e}")

def run_updater_script(new_exe_path):
    current_exe = sys.executable
    updater_filename = "updater.exe"
    temp_dir = tempfile.gettempdir()
    extracted_updater_path = os.path.join(temp_dir, updater_filename)

    try:
        # Get MEIPASS directory where updater.exe is bundled
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        bundled_updater_path = os.path.join(bundle_dir, updater_filename)

        if not os.path.exists(bundled_updater_path):
            raise FileNotFoundError(f"Missing bundled updater: {bundled_updater_path}")

        # Copy updater.exe to a clean temp path
        shutil.copyfile(bundled_updater_path, extracted_updater_path)
        logging.info(f"Copied updater to: {extracted_updater_path}")

        # Launch the updater with paths as args
        subprocess.Popen(
            [extracted_updater_path, new_exe_path, current_exe],
            shell=False,
            close_fds=True
        )

        logging.info("Updater launched successfully. Exiting main app.")
        sys.exit(0)

    except Exception as e:
        logging.exception("Failed to launch updater.")
        QMessageBox.critical(None, "Update Error", f"Could not launch updater:\n{e}")

LOG_FILE = "GameVault-Relocator.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Detect OS type
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

def is_admin():
    """Check if the script is running with administrator/root privileges."""
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.error(f"Error checking admin privileges: {e}")
            return False
    else:
        return os.geteuid() == 0  # Linux/macOS check for root user

# Relaunch with admin/root rights if needed
if not is_admin():
    try:
        if IS_WINDOWS:
            # Relaunch with admin privileges using ShellExecuteW
            script = sys.executable
            params = " ".join(f'"{arg}"' for arg in sys.argv)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        else:
            # Linux/macOS: Relaunch with sudo
            script = sys.argv[0]  # Get the current script path
            params = " ".join(f'"{arg}"' for arg in sys.argv[1:])  # Pass original arguments
            subprocess.run(["sudo", sys.executable, script, *sys.argv[1:]], check=True)

    except Exception as e:
        sys.exit(f"Failed to elevate to admin/root: {str(e)}")

    sys.exit()  # Exit the non-admin process after relaunch

def get_robocopy_thread_count():
    try:
        return min(os.cpu_count() or 4, 32)  # Cap at 32 threads
    except:
        return 4

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
            skipped_files = 0
            failed_files = 0
            start_time = time.time()
            total_bytes_moved = 0
            warnings = []
        
            if hasattr(self, 'preview_mode') and self.preview_mode:
                logging.info("Preview mode enabled — no files will be moved.")
                self.finished.emit(
                    f"[Preview Mode] Would move {total_files} files from:\n{self.source}\nto\n{self.destination}\n"
                    f"Total size: {round(sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(self.source) for f in files) / (1024 ** 3), 2)} GB"
                )
                return

            if getattr(sys, 'frozen', False):
                log_dir = os.path.dirname(sys.executable)
            else:
                log_dir = os.path.abspath(".")

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = os.path.join(log_dir, f"{'robocopy' if self.use_robocopy else 'move'}_{timestamp}.log")

            if IS_WINDOWS:
                if self.use_robocopy:
                    if self.preview_mode:
                        logging.warning("Preview mode is not supported with Robocopy. Falling back to native Python transfer.")
                        self.use_robocopy = False  # fallback
                        return  # Prevent falling through to native move block
                    else:
                        # Proceed with Robocopy as usual
                        thread_count = get_robocopy_thread_count()
                        logging.info(f"Using Robocopy with {thread_count} threads")

                        robocopy_command = [
                            "robocopy", self.source, self.destination,
                            "/E", "/MOVE", "/NP", "/R:3", "/W:2",
                            f"/MT:{thread_count}",
                            "/LOG:" + log_file
                        ]

                        # Add startupinfo to hide the Robocopy console window
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        si.wShowWindow = subprocess.SW_HIDE  # Hides the command prompt window

                        self.robocopy_process = subprocess.Popen(
                            robocopy_command,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            text=True,
                            startupinfo=si  #  This hides the Robocopy window
                        )

                    
                    while self.robocopy_process.poll() is None:
                        if self._stop_requested:
                            self.robocopy_process.terminate()
                            logging.info("Robocopy Transfer canceled by user request.")
                            self.finished.emit("Transfer canceled by user.")
                            return

                        try:
                            with open(log_file, "r", encoding="mbcs", errors="replace") as f:
                                moved_files = 0
                                skipped_files = 0
                                failed_files = 0

                                for line in f:
                                    if "New File" in line or "Moved" in line:
                                        moved_files += 1
                                    elif "Skipped" in line:
                                        skipped_files += 1
                                    elif "EXTRA File" in line or "Access is denied" in line or "ERROR" in line:
                                        failed_files += 1
                        except Exception as e:
                            logging.warning(f"Could not read Robocopy log during progress check: {e}")

                        progress = int((moved_files / total_files) * 100) if total_files > 0 else 0
                        self.progress.emit(progress)
                        self.progress_summary.emit(f"{moved_files}/{total_files} files moved... (Robocopy)")
                        time.sleep(1)

                    if self._stop_requested:
                        logging.info("Transfer canceled by user request.")
                        self.finished.emit("Transfer canceled by user.")
                        return

                    if self.robocopy_process.returncode >= 8:
                        self.finished.emit(f"Robocopy failed: See log file at {log_file}")
                        logging.error(f"Robocopy failed: {log_file}")
                        return

                    if not self._stop_requested and os.path.exists(self.source):
                        has_files = any(
                            os.path.isfile(os.path.join(root, file))
                            for root, _, files in os.walk(self.source)
                            for file in files
                        )
                        if not has_files:
                            if IS_WINDOWS:
                                os.system(f'rmdir /S /Q "{self.source}"')
                            else:
                                shutil.rmtree(self.source, ignore_errors=True)
                            logging.info(f"Source directory removed: {self.source}")
                        else:
                            logging.warning(f"Skipped removing source directory — files still exist: {self.source}")

                else:
                    for root, dirs, files in os.walk(self.source, topdown=False):
                        for file in files:
                            if self._stop_requested:
                                self.finished.emit("Transfer canceled by user.")
                                return

                            src_file = os.path.join(root, file)
                            dest_file = src_file.replace(self.source, self.destination, 1)
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                            try:
                                if self.preview_mode:
                                    log_line = f"[PREVIEW] Would move: {src_file} -> {dest_file}\n"
                                    with open(log_file, 'a', encoding='utf-8') as log_f:
                                        log_f.write(log_line)
                                    moved_files += 1
                                    total_bytes_moved += os.path.getsize(src_file)
                                    continue
   
                                try:
                                    file_size = os.path.getsize(src_file)  # Get size BEFORE move
                                except Exception as e:
                                    file_size = 0
                                    logging.warning(f"Could not get size of {src_file}: {e}")

                                if self.move_with_retries(src_file, dest_file):
                                    moved_files += 1
                                    total_bytes_moved += file_size
                                    with open(log_file, 'a', encoding='utf-8') as log_f:
                                        log_f.write(f"Moved: {src_file} -> {dest_file}\n")
                                else:
                                    failed_files += 1
                                    warnings.append(f"Failed to move: {src_file}")
  
                            except Exception as e:
                                failed_files += 1
                                warnings.append(str(e))
                                logging.error(f"Exception during move: {e}")

                            progress = int((moved_files / total_files) * 100)
                            self.progress_summary.emit(
                                f"{moved_files}/{total_files} files {'previewed' if self.preview_mode else 'moved'}"
                            )
                            self.progress.emit(progress)

                    if self._stop_requested:
                        self.finished.emit("Transfer canceled by user.")
                        return

                    if not self.remove_empty_dirs(self.source):
                        logging.error(f"Manual deletion required for: {self.source}")
                        if IS_WINDOWS:
                            os.system(f'rmdir /S /Q "{self.source}"')
                        else:
                            shutil.rmtree(self.source, ignore_errors=True)

            elif IS_LINUX or IS_MAC:
                rsync_command = [
                    "rsync", "-a", "--remove-source-files", self.source + "/", self.destination + "/"
                ]
                self.rsync_process = subprocess.Popen(
                    rsync_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                while self.rsync_process.poll() is None:
                    if self._stop_requested:
                        self.rsync_process.terminate()
                        self.finished.emit("Transfer canceled by user.")
                        return

                    moved_files = self.count_total_files(self.destination)
                    progress = int((moved_files / total_files) * 100) if total_files > 0 else 0
                    self.progress.emit(progress)
                    time.sleep(1)

                subprocess.run(["find", self.source, "-type", "d", "-empty", "-delete"], check=False)

            elapsed_time = time.time() - start_time
            moved_gb = total_bytes_moved / (1024 ** 3)

            self.progress.emit(100)
            self.finished.emit(
                f"{'Preview' if self.preview_mode else 'Move'} completed to: {self.destination}\n"
                f"Files {'previewed' if self.preview_mode else 'moved'}: {moved_files}, "
                f"Skipped: {skipped_files}, Failed: {failed_files}\n"
                f"Total GB: {moved_gb:.2f}, Time Taken: {elapsed_time:.2f} seconds\n"
                f"Warnings/Errors: {len(warnings)}\n"
                f"Log saved to: {log_file}"
            )
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.finished.emit(error_msg)
            logging.error(error_msg)

    def stop(self):
        self._stop_requested = True
        if self.robocopy_process and self.robocopy_process.poll() is None:
            self.robocopy_process.terminate()
        if self.rsync_process and self.rsync_process.poll() is None:
            self.rsync_process.terminate()


class SymlinkCheckerThread(QThread):
    """Threaded class for checking symlinks on a selected drive"""
    progress = pyqtSignal(str)  # Emits real-time progress updates
    status = pyqtSignal(str)  # Updates status message
    finished = pyqtSignal(str)  # Emits final results

    def __init__(self, drive):
        super().__init__()
        self.drive = drive

    def run(self):
        try:
            if IS_WINDOWS:
                drive_clean = self.drive.split()[0].rstrip("\\/")
                drive_quoted = f'"{drive_clean}\\"' 
                logging.info(f"Starting symlink scan on drive: {drive_quoted}")
                process = subprocess.Popen(
                    f'dir {drive_quoted} /AL /S',
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                logging.debug(f"Running symlink scan command: dir {drive_clean} /AL /S")

            else:
                # On Linux/macOS, use `find` to locate symlinks (fallback approach)
                process = subprocess.Popen(
                    ["find", self.drive, "-type", "l"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

            output_lines = []
            current_dir = ""

            for line in process.stdout:
                line = line.strip()

                # Track current directory from " Directory of ..." lines
                if line.lower().startswith("directory of"):
                    current_dir = line[13:].strip().lower()
                    continue

                if (
                    "<SYMLINK" in line
                    and "JUNCTION" not in line
                    and "$recycle.bin" not in current_dir  # <- skip based on directory context
                ):
                    output_lines.append(line)
                    self.progress.emit("\n".join(output_lines))

            stderr = process.stderr.read()
            process.wait()

            if process.returncode != 0 and "File Not Found" not in stderr:
                logging.error(f"Symlink scan error (exit code {process.returncode}): {stderr}")
                self.finished.emit(f"Error scanning symlinks:\n\n{stderr}")
                return

            if not output_lines:
                logging.info(f"No symlinks found on {self.drive}")
                self.finished.emit("No symlinks found.")
            else:
                logging.info(f"Found {len(output_lines)} symlinks on {self.drive}")
                for entry in output_lines:
                    logging.info(f"  Symlink: {entry}")
                self.finished.emit("\n".join(output_lines))

        except Exception as e:
            error_msg = f"Unexpected error in symlink checker: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            self.finished.emit(f"Error: {e}")

class SymlinkMoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.base_symlink_instruction = (
            "To check for current symlinks, select a drive and click 'Check Symlinks'.<br>"
            "<span style='color:#00ff88; font-style:italic;'>Note: This check can take some time on a large drive with many directories.</span>"
        )
        self.transfer_canceled = False

        self.source_path = None  # Initialize source path
        self.destination_path = None  # Initialize destination path

        self.setWindowTitle(f"GameVault-Relocator v{APP_VERSION}")  # Show version in title
        self.setGeometry(100, 100, 750, 800)  # Set window size
        self.center_window()  # Center the window on the screen

        self.setStyleSheet(self.get_dark_theme())  # Apply Dark Theme
        self.layout = QVBoxLayout()

        # Set button width
        button_width = 400

        # Labels for Source & Destination
        self.source_label = QLabel("Source Directory: Not Selected")
        self.destination_label = QLabel("Destination Root Directory: Not Selected")
        self.layout.addWidget(self.source_label)
        self.layout.addWidget(self.destination_label)

        self.layout.addSpacing(20)

        # Buttons for selecting source and destination
        self.select_source_btn = QPushButton("Select Source Directory")
        self.select_source_btn.setFixedSize(button_width, 30)  # Set width & height
        self.select_source_btn.clicked.connect(self.select_source)
        self.layout.addWidget(self.select_source_btn, alignment=Qt.AlignCenter)

        self.select_destination_btn = QPushButton("Select Destination Root Directory")
        self.select_destination_btn.setFixedSize(button_width, 30)
        self.select_destination_btn.clicked.connect(self.select_destination)
        self.layout.addWidget(self.select_destination_btn, alignment=Qt.AlignCenter)

        # Add spacing between "Select Destination Root Directory" and the checkbox
        self.layout.addSpacing(15)

        if IS_WINDOWS:
            self.use_robocopy_checkbox = QCheckBox("Use Robocopy for moving files")
            self.layout.addWidget(self.use_robocopy_checkbox, alignment=Qt.AlignCenter)

        # Add spacing between the checkbox and "Start Move & Symlink" button
        self.layout.addSpacing(20)

        # Create Symlink Only Button (Blue Color)
        self.symlink_only_btn = QPushButton("Create Symlink Only (No Move)")
        self.symlink_only_btn.setFixedSize(300, 30)
        self.symlink_only_btn.setStyleSheet(
            "QPushButton { background-color: #1e3a8a; color: white; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )

        self.symlink_only_btn.clicked.connect(self.create_symlink_only)
        self.layout.addWidget(self.symlink_only_btn, alignment=Qt.AlignCenter)

        self.layout.addSpacing(20)

        # Start Button (Green Color)
        self.start_btn = QPushButton("Start Move - Create Symlink")
        self.start_btn.setFixedSize(button_width, 30)
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #218838; }"
        )
        self.start_btn.clicked.connect(self.start_process)
        self.layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        
        self.preview_checkbox = QCheckBox("Preview Only (Dry Run – no changes)")
        self.layout.addWidget(self.preview_checkbox, alignment=Qt.AlignCenter)

        # Stop Button (Red) - initially hidden
        self.stop_btn = QPushButton("Cancel Transfer")
        self.stop_btn.setFixedSize(button_width, 30)
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: white; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #c82333; }"
        )
        self.stop_btn.clicked.connect(self.cancel_transfer)
        self.stop_btn.hide()
        self.layout.addWidget(self.stop_btn, alignment=Qt.AlignCenter)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_bar)

        # Progress Summary Label
        self.progress_summary_label = QLabel("")
        self.progress_summary_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_summary_label)

        # Progress Bar (Indeterminate Mode)
        self.scan_progress = QProgressBar()
        self.scan_progress.setAlignment(Qt.AlignCenter)
        self.scan_progress.setRange(0, 0)  # Indeterminate mode
        self.scan_progress.hide()  # Hidden until scanning starts
        self.layout.addWidget(self.scan_progress)

        self.symlink_instruction = QLabel()
        self.symlink_instruction.setTextFormat(Qt.RichText)
        self.symlink_instruction.setWordWrap(True)
        self.symlink_instruction.setAlignment(Qt.AlignCenter)
        self.symlink_instruction.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.symlink_instruction.setMinimumWidth(700)
        self.symlink_instruction.setText(self.base_symlink_instruction)
        self.symlink_instruction.adjustSize()
        self.layout.addWidget(self.symlink_instruction, alignment=Qt.AlignCenter)

        # Set fixed width (match your layout width)
        self.symlink_instruction.setMinimumWidth(700)

        # Set the full text
        self.symlink_instruction.setText(
            "To check for current symlinks, select a drive and click 'Check Symlinks'.<br>"
            "<span style='color:#00DD00; font-style:italic;'><b>Note:</b> This check can take some time on a large drive with many directories.</span>"
        )

        # Force height recalculation
        self.symlink_instruction.adjustSize()

        # Add to layout
        self.layout.addWidget(self.symlink_instruction, alignment=Qt.AlignCenter)


        # Add spacing between these two elements
        self.layout.addSpacing(15)  # Adjust number for more/less space

        # Status Label for Live Updates
        self.scan_status_label = QLabel("Select a drive and click 'Check Symlinks'.")
        self.layout.addWidget(self.scan_status_label, alignment=Qt.AlignCenter)
        
        self.layout.addSpacing(15)
        
        # Drive Selection for Symlink Checking
        self.drive_selection = QComboBox()
        self.drive_selection.addItems(self.get_available_drives())
        self.layout.addWidget(self.drive_selection, alignment=Qt.AlignCenter)

        self.layout.addSpacing(15)
        
        # Button to Check Symlinks
        self.check_symlinks_btn = QPushButton("Check for Symlinks")
        self.check_symlinks_btn.setFixedSize(button_width, 30)
        self.check_symlinks_btn.clicked.connect(self.start_symlink_check)
        self.layout.addWidget(self.check_symlinks_btn, alignment=Qt.AlignCenter)

        # Symlink Results Output
        self.symlink_results = QTextEdit()
        self.symlink_results.setReadOnly(True)
        self.layout.addWidget(self.symlink_results)

        # Add spacing before the Exit button for better UI spacing
        self.layout.addSpacing(20)

        # Button Row Layout
        info_log_row = QHBoxLayout()

        # --- Button Row Layout for Info, Help, and Log ---
        button_row = QHBoxLayout()

        # Create all buttons with identical widths
        self.info_btn = QPushButton("Info")
        self.info_btn.setFixedSize(150, 30)
        self.info_btn.clicked.connect(self.show_info_popup)

        self.help_btn = QPushButton("Help")
        self.help_btn.setFixedSize(150, 30)
        self.help_btn.clicked.connect(self.show_help_popup)

        self.view_log_btn = QPushButton("View Log")
        self.view_log_btn.setFixedSize(150, 30)
        self.view_log_btn.clicked.connect(self.show_log_viewer)

        # Add all buttons to the row with spacing
        button_row.addStretch(1)
        button_row.addWidget(self.info_btn)
        button_row.addSpacing(10)
        button_row.addWidget(self.help_btn)
        button_row.addSpacing(10)
        button_row.addWidget(self.view_log_btn)
        button_row.addStretch(1)

        # Add to main layout
        self.layout.addLayout(button_row)
        self.layout.addSpacing(20)
        
        # Exit Button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFixedSize(150, 30)
        self.exit_btn.clicked.connect(self.close)
        self.layout.addWidget(self.exit_btn, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)
      
    def cancel_transfer(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.transfer_canceled = True  # Mark as canceled
            self.worker._stop_requested = True
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Cancelling...")

            if hasattr(self.worker, 'robocopy_process') and self.worker.robocopy_process:
                try:
                    self.worker.robocopy_process.terminate()
                    logging.info("Robocopy process terminated by user.")
                except Exception as e:
                    logging.warning(f"Failed to terminate Robocopy: {e}")

      
    def show_help_popup(self):
        help_text = r"""
        <h2 style='color: #61afef;'>How to Use GameVault-Relocator</h2>

        <!-- Section 1: Core Usage -->
        <ol style='color: white; font-size: 11pt;'>
        <li><b>Select Source Directory:</b><br>Pick the folder you want to move and create a symlink for.</li><br>
        <li><b>Select Destination Root Drive:</b><br>This is where your files will be moved to.<br>
        For example R:\emulators\rpcs3\games would move to S:\emulators\rpcs3\games. The destination will use the same directory structure as the source directory. 
        Example #2: R:\LaunchBox\Games\Sega Dreamcast → S:\Launchbox\Games\Sega Dreamcast</li><br>
        <li><b>Choose 'Start Move - Create Symlink':</b><br>The app will move files and create a symbolic link at the original source location.</li><br>
        <li><b>Or use 'Create Symlink Only (No Move)':</b><br>Use this if you already moved the files manually and just want to link them back.</li><br>
        <li><b>Check for Symlinks:</b><br>Select a drive and click 'Check for Symlinks' to view all current symbolic links on a drive.</li><br>
        <li><b>View Logs:</b><br>Click 'View Log' to see all actions taken and errors (if any).</li><br>
        </ol>

        <!-- Separator -->
        <hr style='border: 1px solid #61afef; margin: 10px 0;'>

        <!-- Title for update instructions -->
        <h3 style='color: #00ffff;'>🛠 To Update on Linux / macOS</h3>

        <!-- Section 2: Linux/Mac Updater -->
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
        label = QLabel(help_text)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("color: white;")
        layout.addWidget(label)

        ok_button = QPushButton("Close")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)

        dialog.setLayout(layout)
        dialog.exec_()
  
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

        # Buttons row
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
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    open(log_path, 'w').close()
                    text_edit.setText("")  # Clear display
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
        dialog.exec_()

    def create_symlink_only(self):
        if not self.source_path or not self.destination_path:
            QMessageBox.warning(self, "Missing Paths", "Please select both source and destination directories first.")
            return

        source_drive, source_relative_path = os.path.splitdrive(self.source_path)
        source_relative_path = source_relative_path.lstrip("\\")
        destination_final_path = os.path.join(self.destination_path, source_relative_path)

        # Ensure destination exists (but we’re not copying files)
        os.makedirs(destination_final_path, exist_ok=True)

        if os.path.exists(self.source_path):
            try:
                shutil.rmtree(self.source_path)
                logging.info(f"Removed original source: {self.source_path} before symlink-only operation.")
            except Exception as e:
                logging.error(f"Failed to remove source for symlink-only: {e}")
                QMessageBox.critical(self, "Error", f"Could not remove original source folder:\n{e}")
                return

        # Create symlink
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
     
    def show_info_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About GameVault-Relocator")
        dialog.setFixedSize(850, 550)

        def get_resource_path(filename):
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, filename)
            return os.path.join(os.path.abspath("."), filename)

        background_path = get_resource_path("background.jpg")

        # Main container layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create background QLabel and load scaled image
        bg_label = QLabel(dialog)
        pixmap = QPixmap(background_path).scaled(
            dialog.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        bg_label.setPixmap(pixmap)
        bg_label.setGeometry(0, 0, dialog.width(), dialog.height())
        bg_label.lower()

        # Overlay widget for semi-transparent content
        overlay = QWidget(dialog)
        overlay.setGeometry(0, 0, dialog.width(), dialog.height())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);")

        # Overlay layout with info text
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
            '<p style="color:#ffffff;"><b>Other Projects:</b><br>'
            '<a href="https://github.com/ScriptedBits/" style="color:#00ffff;">'
            "https://github.com/ScriptedBits/</a></p>"
        )

        info_label = QLabel(info_text)
        info_label.setOpenExternalLinks(True)
        info_label.setTextFormat(Qt.RichText)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11pt;")
        overlay_layout.addWidget(info_label)

        # OK Button
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
        overlay_layout.addWidget(ok_button, alignment=Qt.AlignCenter)

        dialog.exec_()

    def get_resource_path(filename):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, filename)
        return os.path.join(os.path.abspath("."), filename)

    def center_window(self):
            """Centers the window on the screen."""
            frame_geometry = self.frameGeometry()
            screen_center = QApplication.desktop().screenGeometry().center()
            frame_geometry.moveCenter(screen_center)
            self.move(frame_geometry.topLeft())

    def select_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if folder:
            self.source_path = folder
            self.source_label.setText(f"Source Directory: {folder}")

    def select_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Root Directory")
        if folder:
            self.destination_path = folder
            self.destination_label.setText(f"Destination Root Directory: {folder}")

    def start_process(self):
        if not self.source_path or not self.destination_path:
            QMessageBox.warning(self, "Error", "Please select both source and destination directories.")
            return
        # Clear previous progress summary
        self.progress_summary_label.setText("")
        # Estimate source size
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

            # 🚨 Compare sizes
            if destination_free < estimated_source_size:
                source_gb = round(estimated_source_size / (1024**3), 2)
                dest_gb = round(destination_free / (1024**3), 2)
                QMessageBox.critical(
                    self,
                    "Insufficient Space",
                    f"The destination drive does not have enough free space.\n\n"
                    f"Estimated size of source: {source_gb} GB\n"
                    f"Available space on destination: {dest_gb} GB\n\n"
                    "Please free up space or choose another destination."
                )
                return
        except Exception as e:
            logging.error(f"Drive space check failed: {e}")
            QMessageBox.warning(self, "Drive Space Check Failed", f"Could not verify available space:\n{e}")
            return

        # If space is good, continue with original logic
        source_drive, source_relative_path = os.path.splitdrive(self.source_path)
        source_relative_path = source_relative_path.lstrip("\\")  # Remove leading backslash

        destination_final_path = os.path.join(self.destination_path, source_relative_path)
        # Only create the destination dir if it's not a dry run
        if not self.preview_checkbox.isChecked():
            os.makedirs(destination_final_path, exist_ok=True)

        self.progress_bar.setValue(0)
        self.worker = MoveThread(
            self.source_path,
            destination_final_path,
            self.use_robocopy_checkbox.isChecked(),
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
        # logging.info(f"Move finished: {message}")
        # Hide and reset the Cancel button
        self.stop_btn.hide()
        self.stop_btn.setEnabled(True)
        self.preview_checkbox.setEnabled(True)
        self.stop_btn.setText("Cancel Transfer")
        # Clear the progress summary label
        self.progress_summary_label.setText("")
        self.start_btn.setEnabled(True)
        
        QMessageBox.information(self, "Process Complete", message)
        
        # Skip symlink creation if user canceled
        if self.transfer_canceled:
            logging.info("Transfer was canceled. Skipping symlink creation.")
            self.transfer_canceled = False
            return

        # Preview mode check should be here
        if hasattr(self, 'preview_checkbox') and self.preview_checkbox.isChecked():
            logging.info("Preview mode enabled — skipping symlink creation.")
            return

        # Extract relative path from source
        source_drive, source_relative_path = os.path.splitdrive(self.source_path)
        source_relative_path = source_relative_path.lstrip("\\")

        # Create a symbolic link pointing to the new full path
        destination_final_path = os.path.join(self.destination_path, source_relative_path)

        logging.info(f"Attempting to create symlink: {self.source_path} -> {destination_final_path}")

        # Ensure the original folder is completely removed before creating the symlink
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
                return  # Stop execution if the directory can't be removed

        # Now that the source folder is gone, create the symlink
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
    
    def get_available_drives(self):
        drives = []
        
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
                # Fallback directories if psutil fails
                for base in ["/mnt", "/media", "/Volumes"]:
                    if os.path.exists(base):
                        for item in os.listdir(base):
                            full_path = os.path.join(base, item)
                            if os.path.ismount(full_path):
                                drives.append(full_path)
        return drives

    def start_symlink_check(self):
        selected_drive = self.drive_selection.currentText()
        self.symlink_results.setText("Scanning for symlinks...\nPlease wait...")
        self.symlink_instruction.setText(
            self.base_symlink_instruction +
            f"<br><br><span style='color: #61afef;'>Scanning <b>{selected_drive}</b> for symlinks...</span>"
        )

        self.check_symlinks_btn.setEnabled(False)
        self.scan_progress.show()

        # Start the background thread for checking symlinks
        self.worker = SymlinkCheckerThread(selected_drive)
        self.worker.progress.connect(self.symlink_results.setText)  # Live update
        self.worker.status.connect(self.scan_status_label.setText)  # Show status
        self.worker.finished.connect(self.on_symlink_check_finished)
        self.worker.start()

    def on_symlink_check_finished(self, result):
        self.symlink_instruction.setText(
            self.base_symlink_instruction +
            "<br><br><span style='color: #28a745; font-weight: bold;'>✔ Scan complete!</span>"
        )

        self.symlink_results.setText(result)
        self.scan_progress.hide()
        self.check_symlinks_btn.setEnabled(True)

    def get_dark_theme(self):
        return """
            QWidget { background-color: #282c34; color: #abb2bf; font-size: 12pt; }
            QLabel { color: #ffffff; font-weight: bold; }
            
            /* Smaller Buttons */
            QPushButton { 
                background-color: #61afef; 
                color: black; 
                border-radius: 4px; 
                padding: 4px; 
                font-size: 10pt;  /* Smaller font */
                min-height: 24px; /* Reduce button height */
            }
            QPushButton:hover { background-color: #528bbf; }

            /* Green Progress Bar */
            QProgressBar {
                border: 2px solid #3c4049;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                background-color: #3c4049;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #28a745;  /* Green */
                width: 20px;
            }

            /* Other Elements */
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
    check_for_updates()  # optional here, or triggered from init
    sys.exit(app.exec_())
