import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QSize, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
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
    QSizePolicy,
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

SIDEBAR_ITEMS = (
    ("\U0001F4C4", "Convert", ".cap, .pcap, .pcapng"),
    ("#", "Generate", "Hashcat 22000"),
    ("\U0001F5B1", "Drag & Drop", "File Support"),
    ("\U0001F4DA", "Batch", "Conversion"),
    ("\U0001F6E1", "Offline", "Operation"),
    ("\U0001F680", "Fast &", "Efficient"),
)


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
                self.status_signal.emit(index, "Completed")

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
        self.resize(1400, 900)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.setAcceptDrops(True)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        self.setup_header(root)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        self.setup_sidebar(body)
        self.setup_main_panel(body)

        self.setup_footer(root)

        self.apply_theme()

    # ------------------------------------------------------------------
    # Header: logo, product name, version badge, subtitle
    # ------------------------------------------------------------------
    def setup_header(self, layout):
        header = QHBoxLayout()
        header.setSpacing(16)

        logo = QLabel()
        logo.setObjectName("logoBadge")
        logo.setFixedSize(72, 72)
        logo.setAlignment(Qt.AlignCenter)

        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(
                56,
                56,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            logo.setPixmap(pixmap)
        else:
            logo.setText("\U0001F43E")
            logo.setFont(QFont("Segoe UI", 26))

        header.addWidget(logo)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title = QLabel("HashCatcher")
        title.setObjectName("appTitle")
        title_font = QFont("Segoe UI", 28, QFont.Bold)
        title_font.setStyleHint(QFont.SansSerif)
        title.setFont(title_font)
        title_row.addWidget(title)

        badge = QLabel("v1.0")
        badge.setObjectName("versionBadge")
        badge.setAlignment(Qt.AlignCenter)
        title_row.addWidget(badge)
        title_row.addStretch(1)

        subtitle = QLabel("Offline Wireless Capture → Hashcat 22000 Converter")
        subtitle.setObjectName("subtitle")

        title_block.addLayout(title_row)
        title_block.addWidget(subtitle)

        header.addLayout(title_block, 1)
        layout.addLayout(header)

    # ------------------------------------------------------------------
    # Sidebar: static feature legend, mirrors the product's capabilities
    # ------------------------------------------------------------------
    def setup_sidebar(self, layout):
        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(190)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(10)

        for icon, title, subtitle in SIDEBAR_ITEMS:
            sidebar_layout.addWidget(self._make_sidebar_item(icon, title, subtitle))

        sidebar_layout.addStretch(1)
        layout.addWidget(sidebar)

    def _make_sidebar_item(self, icon, title, subtitle):
        item = QFrame()
        item.setObjectName("sidebarItem")

        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(8, 8, 8, 8)
        item_layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("sidebarIcon")
        icon_label.setFixedSize(30, 30)
        icon_label.setAlignment(Qt.AlignCenter)
        item_layout.addWidget(icon_label)

        text_block = QVBoxLayout()
        text_block.setSpacing(0)

        title_label = QLabel(title)
        title_label.setObjectName("sidebarTitle")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("sidebarSubtitle")

        text_block.addWidget(title_label)
        text_block.addWidget(subtitle_label)

        item_layout.addLayout(text_block, 1)
        return item

    # ------------------------------------------------------------------
    # Main panel: drop zone + queue table + progress/controls
    # ------------------------------------------------------------------
    def setup_main_panel(self, layout):
        main_card = QFrame()
        main_card.setObjectName("card")

        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        self.setup_drop_zone(content_row)
        self.setup_table(content_row)

        main_layout.addLayout(content_row, 1)

        self.setup_progress(main_layout)
        self.setup_toolbar(main_layout)
        self.setup_logs(main_layout)

        layout.addWidget(main_card, 1)

    def setup_drop_zone(self, layout):
        drop = QFrame()
        drop.setObjectName("dropZone")
        drop.setFixedWidth(300)

        drop_layout = QVBoxLayout(drop)
        drop_layout.setContentsMargins(16, 24, 16, 16)
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

    def setup_table(self, layout):
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("queueTable")

        self.table.setHorizontalHeaderLabels([
            "File",
            "Type",
            "Size",
            "Status",
            "Output",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.table.setColumnWidth(0, 190)
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
        self.logs.setMinimumHeight(140)
        self.logs.setMaximumHeight(180)

        layout.addWidget(self.logs)

    # ------------------------------------------------------------------
    # Footer: supported formats, output format, security notice
    # ------------------------------------------------------------------
    def setup_footer(self, layout):
        footer = QFrame()
        footer.setObjectName("card")

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 14, 18, 14)
        footer_layout.setSpacing(20)

        in_block = QVBoxLayout()
        in_block.addWidget(self._section_label("SUPPORTED INPUT FORMATS"))
        in_row = QHBoxLayout()
        for ext in (".cap", ".pcap", ".pcapng"):
            in_row.addWidget(self._format_chip(ext))
        in_row.addStretch(1)
        in_block.addLayout(in_row)
        footer_layout.addLayout(in_block, 1)

        arrow = QLabel("→")
        arrow.setObjectName("footerArrow")
        arrow.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(arrow)

        out_block = QVBoxLayout()
        out_block.addWidget(self._section_label("OUTPUT FORMAT"))
        out_row = QHBoxLayout()
        out_row.addWidget(self._format_chip("22000", detail="Hashcat 22000 Format"))
        out_row.addStretch(1)
        out_block.addLayout(out_row)
        footer_layout.addLayout(out_block, 1)

        notice = QFrame()
        notice.setObjectName("securityNotice")
        notice_layout = QHBoxLayout(notice)
        notice_layout.setContentsMargins(12, 8, 12, 8)
        notice_icon = QLabel("\U0001F6E1")
        notice_text = QLabel(
            "For authorized security testing\nand educational use only."
        )
        notice_text.setObjectName("securityNoticeText")
        notice_layout.addWidget(notice_icon)
        notice_layout.addWidget(notice_text)
        footer_layout.addWidget(notice)

        layout.addWidget(footer)

    def _section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _format_chip(self, ext, detail=None):
        chip = QFrame()
        chip.setObjectName("formatChip")

        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(10, 6, 10, 6)
        chip_layout.setSpacing(6)

        icon = QLabel("\U0001F4C4")
        chip_layout.addWidget(icon)

        text_block = QVBoxLayout()
        text_block.setSpacing(0)

        ext_label = QLabel(ext)
        ext_label.setObjectName("formatChipLabel")
        text_block.addWidget(ext_label)

        if detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("formatChipDetail")
            text_block.addWidget(detail_label)

        chip_layout.addLayout(text_block)
        return chip

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, #central {
                background-color: #141017;
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

            #versionBadge {
                background-color: rgba(194, 24, 91, 0.25);
                color: #ff8fae;
                border-radius: 10px;
                padding: 2px 10px;
                font-weight: bold;
                font-size: 9pt;
            }

            #subtitle {
                color: #9c8a90;
                font-size: 10pt;
            }

            #logoBadge {
                background-color: #1c141a;
                border: 1px solid #3a222c;
                border-radius: 16px;
            }

            #card {
                background-color: #1a1317;
                border: 1px solid #2b1620;
                border-radius: 14px;
            }

            #sidebarItem {
                background-color: #211720;
                border-radius: 10px;
            }

            #sidebarIcon {
                background-color: rgba(194, 24, 91, 0.2);
                border-radius: 8px;
                font-size: 13pt;
            }

            #sidebarTitle {
                font-weight: bold;
                font-size: 10pt;
                color: #f5f5f5;
            }

            #sidebarSubtitle {
                color: #9c8a90;
                font-size: 8.5pt;
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
                gridline-color: #2b1620;
            }

            QHeaderView::section {
                background-color: #1c141a;
                color: #d9a0b2;
                border: none;
                padding: 6px;
                font-weight: bold;
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

            #sectionLabel {
                color: #9c8a90;
                font-size: 8.5pt;
                font-weight: bold;
                letter-spacing: 1px;
            }

            #formatChip {
                background-color: #211720;
                border-radius: 8px;
            }

            #formatChipLabel {
                font-weight: bold;
                color: #f5f5f5;
                font-size: 9.5pt;
            }

            #formatChipDetail {
                color: #9c8a90;
                font-size: 8pt;
            }

            #footerArrow {
                color: #ff4d7a;
                font-size: 16pt;
                font-weight: bold;
            }

            #securityNotice {
                background-color: rgba(194, 24, 91, 0.12);
                border: 1px solid rgba(194, 24, 91, 0.3);
                border-radius: 10px;
            }

            #securityNoticeText {
                color: #d9a0b2;
                font-size: 8.5pt;
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

        file_path = Path(file)

        try:
            size = round(file_path.stat().st_size / 1024 / 1024, 2)
            size_text = f"{size} MB"
        except OSError:
            size_text = "N/A"

        self.table.setItem(row, 0, QTableWidgetItem(file_path.name))
        self.table.setItem(row, 1, QTableWidgetItem(file_path.suffix))
        self.table.setItem(row, 2, QTableWidgetItem(size_text))
        self.table.setItem(row, 3, QTableWidgetItem("Queued"))
        self.table.setItem(
            row,
            4,
            QTableWidgetItem(str(file_path.with_suffix(".22000"))),
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
        self.status_label.setText("All files converted.")
        self.add_log("[INFO] Conversion batch finished.")

    def set_controls_enabled(self, enabled):
        self.add_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)

    def update_status(self, row, status):
        self.table.setItem(row, 3, QTableWidgetItem(status))

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
