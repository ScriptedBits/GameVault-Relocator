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
import shutil
import ctypes
import subprocess
import time
import platform
import logging

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, 
    QMessageBox, QCheckBox, QProgressBar, QComboBox, QTextEdit, QSpacerItem, QSizePolicy, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

APP_VERSION = "1.4.0"

# Setup logging
LOG_FILE = "GameVault-Relocator.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("GameVault-Relocator started")

# Detect OS type
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

def is_admin():
    """Check if the script is running with administrator/root privileges."""
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
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

class MoveThread(QThread):
    """Threaded class to move files and update progress"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, source, destination, use_robocopy):
        super().__init__()
        self.source = source
        self.destination = destination
        self.use_robocopy = use_robocopy

    def count_total_files(self, path):
        """Counts total files recursively in the source directory."""
        total_files = sum(len(files) for _, _, files in os.walk(path))
        return total_files

    def move_with_retries(self, src, dest, retries=5, delay=2):
        """Move a file with retries if it's in use."""
        for attempt in range(1, retries + 1):
            try:
                shutil.move(src, dest)
                logging.info(f"Moved: {src} -> {dest}")
                return True  # Success
            except PermissionError:
                logging.warning(f"Attempt {attempt}: File in use - {src}")
                time.sleep(delay)
            except Exception as e:
                logging.error(f"Error moving file {src}: {e}")
                return False
        return False  # If all retries fail

    def remove_empty_dirs(self, path, retries=3, delay=2):
        """Recursively remove empty directories with retry logic."""
        for attempt in range(1, retries + 1):
            try:
                for root, dirs, _ in os.walk(path, topdown=False):
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        if not os.listdir(dir_path):  # If empty, remove
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

            moved_files = 0  # Counter for progress tracking

            if IS_WINDOWS:
                if self.use_robocopy:
                    # Use Robocopy for Windows
                    log_file = os.path.join(os.path.dirname(self.destination), "robocopy.log")
                    robocopy_command = [
                        "robocopy", self.source, self.destination, "/E", "/MOVE", "/NP", "/R:3", "/W:2", "/LOG:" + log_file
                    ]
                    process = subprocess.Popen(robocopy_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

                    while process.poll() is None:
                        if os.path.exists(log_file):
                            with open(log_file, "r", encoding="utf-8") as f:
                                moved_files = sum(1 for line in f if "New File" in line or "Moved" in line)

                        progress = int((moved_files / total_files) * 100) if total_files > 0 else 0
                        self.progress.emit(progress)
                        time.sleep(1)

                    process.wait()
                    if process.returncode >= 8:
                        self.finished.emit(f"Robocopy failed: See log file at {log_file}")
                        logging.error(f"Robocopy failed: {log_file}")
                        return

                    if os.path.exists(self.source):
                        os.system(f'rmdir /S /Q "{self.source}"')

                    if os.path.exists(log_file):
                        os.remove(log_file)

                else:
                    # Use Native Windows Move (shutil.move)
                    for root, dirs, files in os.walk(self.source, topdown=False):
                        for file in files:
                            src_file = os.path.join(root, file)
                            dest_file = src_file.replace(self.source, self.destination, 1)
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                            if self.move_with_retries(src_file, dest_file):
                                moved_files += 1
                            else:
                                logging.error(f"Failed to move: {src_file}")

                            progress = int((moved_files / total_files) * 100)
                            self.progress.emit(progress)

                        # Remove empty directories after all files in them are moved
                        for dir in dirs:
                            dir_path = os.path.join(root, dir)
                            try:
                                os.rmdir(dir_path)  # Only removes if empty
                                logging.info(f"Removed empty dir: {dir_path}")
                            except OSError:
                                logging.warning(f"Could not remove dir: {dir_path}")

                    # Final cleanup of remaining empty dirs
                    if not self.remove_empty_dirs(self.source):
                        logging.error(f"Manual deletion required for: {self.source}")
                        os.system(f'rmdir /S /Q "{self.source}"')  # Last resort

            elif IS_LINUX or IS_MAC:
                # Use rsync for Linux/macOS
                rsync_command = [
                    "rsync", "-a", "--remove-source-files", self.source + "/", self.destination + "/"
                ]
                process = subprocess.Popen(
                    rsync_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                while process.poll() is None:
                    moved_files = self.count_total_files(self.destination)
                    progress = int((moved_files / total_files) * 100) if total_files > 0 else 0
                    self.progress.emit(progress)
                    time.sleep(1)

                # Remove empty directories after rsync completes
                subprocess.run(["find", self.source, "-type", "d", "-empty", "-delete"], check=False)

            self.progress.emit(100)
            self.finished.emit(f"Move completed to: {self.destination}")
            logging.info(f"Move completed: {self.source} -> {self.destination}")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.finished.emit(error_msg)
            logging.error(error_msg)

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
            self.status.emit("Scanning for symlinks... Please wait...")  # Show "Please wait" message

            process = subprocess.Popen(
                f'dir {self.drive} /AL /S', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            output_lines = []
            for line in process.stdout:
                if "<SYMLINK" in line and "JUNCTION" not in line:  # Only keep true symlinks, not junctions
                    output_lines.append(line.strip())
                    self.progress.emit("\n".join(output_lines))  # Show symlinks in real-time

            process.wait()
            if not output_lines:
                self.finished.emit("No symlinks found.")
            else:
                self.finished.emit("\n".join(output_lines))

        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")

class SymlinkMoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.source_path = None  # Initialize source path
        self.destination_path = None  # Initialize destination path

        self.setWindowTitle(f"GameVault-Relocator v{APP_VERSION}")  # Show version in title
        self.setGeometry(100, 100, 750, 700)  # Set window size
        self.center_window()  # Center the window on the screen

        self.setStyleSheet(self.get_dark_theme())  # Apply Dark Theme
        self.layout = QVBoxLayout()

        # Set button width (adjust as needed)
        button_width = 400

        # Labels for Source & Destination
        self.source_label = QLabel("Source Directory: Not Selected")
        self.destination_label = QLabel("Destination Root Directory: Not Selected")
        self.layout.addWidget(self.source_label)
        self.layout.addWidget(self.destination_label)

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

        # Start Button (Green Color)
        self.start_btn = QPushButton("Start Move - Create Symlink")
        self.start_btn.setFixedSize(button_width, 30)
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #218838; }"
        )
        self.start_btn.clicked.connect(self.start_process)
        self.layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_bar)

        # Progress Bar (Indeterminate Mode)
        self.scan_progress = QProgressBar()
        self.scan_progress.setAlignment(Qt.AlignCenter)
        self.scan_progress.setRange(0, 0)  # Indeterminate mode
        self.scan_progress.hide()  # Hidden until scanning starts
        self.layout.addWidget(self.scan_progress)

        # Instruction Label for Symlink Check
        self.symlink_instruction = QLabel(
            "To check for current symlinks, pick a drive and click 'Check'.\n"
            "Note: This check can take some time on a large drive with many directories."
        )
        self.symlink_instruction.setWordWrap(True)
        self.layout.addWidget(self.symlink_instruction)

        # Add spacing between these two elements
        self.layout.addSpacing(15)  # Adjust number for more/less space

        # Status Label for Live Updates
        self.scan_status_label = QLabel("Select a drive and click 'Check Symlinks'.")
        self.layout.addWidget(self.scan_status_label)

        # Drive Selection for Symlink Checking
        self.drive_selection = QComboBox()
        self.drive_selection.addItems(self.get_available_drives())
        self.layout.addWidget(self.drive_selection, alignment=Qt.AlignCenter)

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

        # Info Button
        self.info_btn = QPushButton("Info")
        self.info_btn.setFixedSize(150, 30)
        self.info_btn.clicked.connect(self.show_info_popup)
        self.layout.addWidget(self.info_btn, alignment=Qt.AlignCenter)
        self.layout.addSpacing(20)
        # Exit Button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFixedSize(150, 30)  # Set a smaller width
        self.exit_btn.clicked.connect(self.close)  # Close the app when clicked
        self.layout.addWidget(self.exit_btn, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)
     
    def show_info_popup(self):
        """Displays an information pop-up with project details."""
        dialog = QDialog(self)
        dialog.setWindowTitle("About GameVault-Relocator")
        dialog.setFixedSize(850, 550)  # Increased height for better spacing

        # Updated Info text with custom link colors
        info_text = (
            f"<h2>GameVault-Relocator v{APP_VERSION}</h2>"
            "<p><b>Created by:</b> ScriptedBits</p>"
            "<p>GameVault-Relocator is a passion project designed to save time by automating moving folders "
            "to another storage device or drive and creating a symlink to the source drive.</p>"
            '<p><b>Project URL:</b><br> <a href="https://github.com/ScriptedBits/GameVault-Relocator" '
            'style="color:#61afef; text-decoration:none;">'
            "https://github.com/ScriptedBits/GameVault-Relocator</a></p>"
            "<p><b>Please check out our other Retro Gaming projects at:</b></p>"
            '<p><a href="https://github.com/ScriptedBits/" '
            'style="color:#61afef; text-decoration:none;">'
            "https://github.com/ScriptedBits/</a></p>"
        )

        # Create layout for the dialog
        layout = QVBoxLayout()

        # Create and set the label with rich text
        label = QLabel(info_text)
        label.setOpenExternalLinks(True)  # Allow clickable links
        label.setWordWrap(True)
        layout.addWidget(label)

        # OK Button to close the dialog
        ok_button = QPushButton("OK")
        ok_button.setFixedSize(100, 30)
        ok_button.clicked.connect(dialog.accept)  # Close the dialog when clicked
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)

        # Apply layout and show the dialog
        dialog.setLayout(layout)
        dialog.exec_()
     
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

        # Extract relative path from source
        source_drive, source_relative_path = os.path.splitdrive(self.source_path)
        source_relative_path = source_relative_path.lstrip("\\")  # Remove leading backslash if present

        # Create the full path in the destination
        destination_final_path = os.path.join(self.destination_path, source_relative_path)

        # Ensure the full directory structure exists
        os.makedirs(destination_final_path, exist_ok=True)

        self.progress_bar.setValue(0)
        self.worker = MoveThread(self.source_path, destination_final_path, self.use_robocopy_checkbox.isChecked())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_move_finished)
        self.worker.start()
        
    def on_move_finished(self, message):
        """Handles actions after the move operation is completed."""
        QMessageBox.information(self, "Process Complete", message)
        logging.info(f"Move finished: {message}")

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
        return [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]

    def start_symlink_check(self):
        selected_drive = self.drive_selection.currentText()
        self.symlink_results.setText("Scanning for symlinks...\nPlease wait...")
        self.scan_status_label.setText(f"Scanning {selected_drive}...")  # Show live scan message
        self.check_symlinks_btn.setEnabled(False)  # Disable button while scanning
        self.scan_progress.show()  # Show progress bar

        # Start the background thread for checking symlinks
        self.worker = SymlinkCheckerThread(selected_drive)
        self.worker.progress.connect(self.symlink_results.setText)  # Live update
        self.worker.status.connect(self.scan_status_label.setText)  # Show status
        self.worker.finished.connect(self.on_symlink_check_finished)
        self.worker.start()

    def on_symlink_check_finished(self, result):
        self.symlink_results.setText(result)
        self.scan_status_label.setText("Scan complete!")  # Show completion message
        self.scan_progress.hide()  # Hide progress bar
        self.check_symlinks_btn.setEnabled(True)  # Re-enable button

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
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SymlinkMoverApp()
    window.show()
    sys.exit(app.exec_())
