import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

HCXPCAPNGTOOL = "hcxpcapngtool"
CAPTURE_EXTENSIONS = (".cap", ".pcap", ".pcapng")
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "hashcather-logo.png"

STATUS_STYLE = {
    "Queued": ("○", "#9c8a90"),
    "Converting": ("⟳", "#e0a94d"),
    "Converted": ("✔", "#4caf7d"),
    "Failed": ("✖", "#e05a5a"),
    "Missing": ("⚠", "#e0a94d"),
}


class ConversionWorker(QThread):
    """Runs hcxpcapngtool against a batch of capture files, one at a time."""

    log_signal = Signal(str)
    progress_signal = Signal(int)
    status_signal = Signal(int, str)
    finished_signal = Signal()

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        total = len(self.files)

        for index, file in enumerate(self.files):
            output = str(Path(file).with_suffix(".22000"))

            if not Path(file).is_file():
                self.log_signal.emit(f"[ERROR] File no longer exists: {file}")
                self.status_signal.emit(index, "Missing")
                self._advance(index, total)
                continue

            self.log_signal.emit(f"[INFO] Converting: {file}")
            self.status_signal.emit(index, "Converting")

            command = [HCXPCAPNGTOOL, "-o", output, file]

            try:
                result = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                if result.stderr.strip():
                    self.log_signal.emit(f"[INFO] {result.stderr.strip()}")

                self.log_signal.emit(f"[SUCCESS] Generated: {output}")
                self.status_signal.emit(index, "Converted")

            except subprocess.CalledProcessError as e:
                detail = (e.stderr or e.stdout or str(e)).strip()
                self.log_signal.emit(f"[ERROR] {file}: {detail}")
                self.status_signal.emit(index, "Failed")

            except Exception as e:
                self.log_signal.emit(f"[ERROR] {file}: {e}")
                self.status_signal.emit(index, "Failed")

            self._advance(index, total)

        self.finished_signal.emit()

    def _advance(self, index, total):
        progress = int(((index + 1) / total) * 100)
        self.progress_signal.emit(progress)


class HashCatcher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.files = []
        self.worker = None

        self.setWindowTitle("HashCatcher")
        self.resize(1200, 780)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.setAcceptDrops(True)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        self.setup_header(root)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        root.addLayout(content_row, 1)

        self.setup_drop_zone(content_row)
        self.setup_table(content_row)

        self.setup_progress(root)
        self.setup_toolbar(root)
        self.setup_logs(root)

        self.apply_theme()

    # ------------------------------------------------------------------
    # Header: just the logo and the program name
    # ------------------------------------------------------------------
    def setup_header(self, layout):
        header = QHBoxLayout()
        header.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(36, 36)
        logo.setAlignment(Qt.AlignCenter)

        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(
                36,
                36,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            logo.setPixmap(pixmap)
        else:
            logo.setText("\U0001F43E")
            logo.setFont(QFont("Segoe UI", 16))

        header.addWidget(logo)

        title = QLabel("HashCatcher")
        title.setObjectName("appTitle")
        title_font = QFont("Segoe UI", 18, QFont.Bold)
        title_font.setStyleHint(QFont.SansSerif)
        title.setFont(title_font)
        header.addWidget(title)

        header.addStretch(1)
        layout.addLayout(header)

    # ------------------------------------------------------------------
    # Drop zone
    # ------------------------------------------------------------------
    def setup_drop_zone(self, layout):
        drop = QFrame()
        drop.setObjectName("dropZone")
        drop.setFixedWidth(280)

        drop_layout = QVBoxLayout(drop)
        drop_layout.setContentsMargins(16, 20, 16, 16)
        drop_layout.setSpacing(10)
        drop_layout.setAlignment(Qt.AlignHCenter)

        files_label = QLabel("\U0001F4C1 Files")
        files_label.setObjectName("dropZoneHeading")
        drop_layout.addWidget(files_label)

        icon = QLabel("☁")
        icon.setObjectName("dropZoneIcon")
        icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(icon)

        hint = QLabel("Drag & drop capture files here\nor click to browse")
        hint.setObjectName("dropZoneHint")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        drop_layout.addWidget(hint)

        self.add_btn = QPushButton("Browse Files")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self.add_files)
        drop_layout.addWidget(self.add_btn)

        drop_layout.addStretch(1)

        self.files_count_label = QLabel("0 files loaded")
        self.files_count_label.setObjectName("dropZoneHint")
        drop_layout.addWidget(self.files_count_label)

        layout.addWidget(drop)

    # ------------------------------------------------------------------
    # Queue table
    # ------------------------------------------------------------------
    def setup_table(self, layout):
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("queueTable")

        self.table.setHorizontalHeaderLabels([
            "File Name",
            "Type",
            "Size",
            "Status",
            "Output",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)

        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 110)

        layout.addWidget(self.table, 1)

    def setup_progress(self, layout):
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

    def setup_toolbar(self, layout):
        toolbar = QHBoxLayout()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        toolbar.addWidget(self.status_label, 1)

        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.setObjectName("secondaryBtn")
        self.clear_btn.clicked.connect(self.clear_queue)

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.clicked.connect(self.convert_files)

        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.convert_btn)

        layout.addLayout(toolbar)

    def setup_logs(self, layout):
        self.logs = QTextEdit()
        self.logs.setObjectName("logPanel")
        self.logs.setReadOnly(True)
        self.logs.setMinimumHeight(120)
        self.logs.setMaximumHeight(160)

        layout.addWidget(self.logs)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, #central {
                background-color: #14101a;
            }

            QWidget {
                background-color: transparent;
                color: #f5f5f5;
                font-family: Segoe UI;
                font-size: 11pt;
            }

            #appTitle {
                color: #ffffff;
            }

            #dropZone {
                background-color: #1c1419;
                border: 2px dashed #4a2634;
                border-radius: 12px;
            }

            #dropZoneHeading {
                color: #d9a0b2;
                font-weight: bold;
            }

            #dropZoneIcon {
                color: #ff4d7a;
                font-size: 30pt;
            }

            #dropZoneHint {
                color: #9c8a90;
                font-size: 9.5pt;
            }

            #statusLabel {
                color: #9c8a90;
            }

            QPushButton#primaryBtn {
                background-color: #c2185b;
                border-radius: 10px;
                padding: 10px 18px;
                color: white;
                font-weight: bold;
            }

            QPushButton#primaryBtn:hover {
                background-color: #ff4d7a;
            }

            QPushButton#primaryBtn:disabled {
                background-color: #5c2634;
                color: #9c8a90;
            }

            QPushButton#secondaryBtn {
                background-color: #241019;
                border: 1px solid #3a222c;
                border-radius: 10px;
                padding: 10px 18px;
                color: #e0c8d0;
                font-weight: bold;
            }

            QPushButton#secondaryBtn:hover {
                background-color: #30141f;
            }

            QPushButton#secondaryBtn:disabled {
                color: #6a5a60;
            }

            QTableWidget#queueTable {
                background-color: #140b10;
                border: 1px solid #2b1620;
                border-radius: 10px;
            }

            QTableWidget#queueTable::item {
                border-bottom: 1px solid #241420;
            }

            QHeaderView::section {
                background-color: #1c141a;
                color: #d9a0b2;
                border: none;
                border-bottom: 1px solid #2b1620;
                padding: 8px 6px;
                font-weight: bold;
            }

            #rowFileName {
                color: #f5f5f5;
                font-weight: bold;
                font-size: 9.5pt;
            }

            #rowFilePath {
                color: #7a6a70;
                font-size: 8pt;
            }

            #rowIcon {
                color: #d9a0b2;
            }

            #typePill {
                background-color: rgba(194, 24, 91, 0.25);
                color: #ff8fae;
                border-radius: 8px;
                padding: 2px 10px;
                font-size: 8.5pt;
                font-weight: bold;
            }

            #rowOutput {
                color: #c9b8bf;
                font-size: 9pt;
            }

            QPushButton#openFolderBtn {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #9c8a90;
                font-size: 11pt;
                padding: 0px;
            }

            QPushButton#openFolderBtn:hover {
                background-color: #241019;
                color: #ff8fae;
            }

            QTextEdit#logPanel {
                background-color: #110a0e;
                border: 1px solid #2b1620;
                border-radius: 10px;
                font-family: Consolas, monospace;
                font-size: 9.5pt;
            }

            QProgressBar {
                border-radius: 8px;
                background-color: #241019;
                height: 12px;
            }

            QProgressBar::chunk {
                background-color: #ff4d7a;
                border-radius: 8px;
            }
        """)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def add_log(self, message):
        self.logs.append(message)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Capture Files",
            "",
            "Capture Files (*.cap *.pcap *.pcapng)",
        )

        for file in files:
            if file not in self.files:
                self.files.append(file)
                self.add_file_to_table(file)

        self._update_files_count()

    def add_file_to_table(self, file):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 54)

        file_path = Path(file)

        # File name + path
        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(10, 4, 4, 4)
        file_layout.setSpacing(8)

        icon = QLabel("\U0001F4C4")
        icon.setObjectName("rowIcon")
        file_layout.addWidget(icon)

        text_block = QVBoxLayout()
        text_block.setSpacing(0)

        name_label = QLabel(file_path.name)
        name_label.setObjectName("rowFileName")
        path_label = QLabel(str(file_path.parent))
        path_label.setObjectName("rowFilePath")

        text_block.addWidget(name_label)
        text_block.addWidget(path_label)
        file_layout.addLayout(text_block, 1)

        self.table.setCellWidget(row, 0, file_widget)

        # Type pill
        type_wrap = QWidget()
        type_wrap_layout = QHBoxLayout(type_wrap)
        type_wrap_layout.setContentsMargins(0, 0, 0, 0)
        type_wrap_layout.addStretch(1)

        type_label = QLabel(file_path.suffix)
        type_label.setObjectName("typePill")
        type_label.setAlignment(Qt.AlignCenter)
        type_wrap_layout.addWidget(type_label)
        type_wrap_layout.addStretch(1)

        self.table.setCellWidget(row, 1, type_wrap)

        # Size
        try:
            size = round(file_path.stat().st_size / 1024 / 1024, 2)
            size_text = f"{size} MB"
        except OSError:
            size_text = "N/A"

        size_item = QTableWidgetItem(size_text)
        size_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, size_item)

        # Status
        status_label = QLabel()
        status_label.setAlignment(Qt.AlignCenter)
        self._apply_status(status_label, "Queued")
        self.table.setCellWidget(row, 3, status_label)

        # Output
        output_path = file_path.with_suffix(".22000")

        out_widget = QWidget()
        out_layout = QHBoxLayout(out_widget)
        out_layout.setContentsMargins(6, 4, 6, 4)
        out_layout.setSpacing(6)

        out_label = QLabel(output_path.name)
        out_label.setObjectName("rowOutput")
        out_layout.addWidget(out_label, 1)

        open_btn = QPushButton("\U0001F4C2")
        open_btn.setObjectName("openFolderBtn")
        open_btn.setFixedSize(26, 26)
        open_btn.setToolTip("Open containing folder")
        open_btn.clicked.connect(
            lambda _checked=False, p=output_path: self.open_output_folder(p)
        )
        out_layout.addWidget(open_btn)

        self.table.setCellWidget(row, 4, out_widget)

    def _apply_status(self, label, status):
        icon, color = STATUS_STYLE.get(status, ("", "#9c8a90"))
        label.setText(f"{icon} {status}")
        label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 9.5pt;")

    def open_output_folder(self, path):
        folder = Path(path).parent
        if folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            QMessageBox.information(
                self,
                "Folder Not Found",
                f"{folder} does not exist yet.",
            )

    def _update_files_count(self):
        count = len(self.files)
        noun = "file" if count == 1 else "files"
        self.files_count_label.setText(f"{count} {noun} loaded")

    def clear_queue(self):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Conversion Running",
                "Please wait for the current conversion to finish.",
            )
            return

        self.files.clear()
        self.table.setRowCount(0)
        self.logs.clear()
        self.progress.setValue(0)
        self.status_label.setText("Ready")
        self._update_files_count()

    def convert_files(self):
        if not self.files:
            QMessageBox.warning(
                self,
                "No Files",
                "Please add capture files.",
            )
            return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Conversion Running",
                "A conversion is already in progress.",
            )
            return

        if not self.check_hcxtools():
            QMessageBox.critical(
                self,
                "hcxtools Missing",
                "hcxpcapngtool was not found on PATH.\n\n"
                "Install hcxtools and ensure it is reachable from a terminal.",
            )
            return

        self.set_controls_enabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Converting...")

        self.worker = ConversionWorker(list(self.files))

        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.status_signal.connect(self.update_status)
        self.worker.finished_signal.connect(self.on_conversion_finished)

        self.worker.start()

    def on_conversion_finished(self):
        self.set_controls_enabled(True)
        self.status_label.setText("✓ All files converted successfully!")
        self.add_log("[INFO] Conversion batch finished.")

    def set_controls_enabled(self, enabled):
        self.add_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)

    def update_status(self, row, status):
        widget = self.table.cellWidget(row, 3)
        if widget is not None:
            self._apply_status(widget, status)

    def check_hcxtools(self):
        return shutil.which(HCXPCAPNGTOOL) is not None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file = url.toLocalFile()

            if file.lower().endswith(CAPTURE_EXTENSIONS):
                if file not in self.files:
                    self.files.append(file)
                    self.add_file_to_table(file)

        self._update_files_count()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = HashCatcher()
    window.show()

    sys.exit(app.exec())
