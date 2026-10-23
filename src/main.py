import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, QByteArray, QSettings, Signal
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

HCXPCAPNGTOOL = "hcxpcapngtool"
HASHCAT = "hashcat"
CAPTURE_EXTENSIONS = (".cap", ".pcap", ".pcapng")
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "hashcather-logo.png"
APP_VERSION = "1.0.0"
DEFAULT_THREADS = 4

PINK = "#ff5c89"
PINK_STRONG = "#ff4d7a"
GRAY_TEXT = "#e0e0e0"
MUTED = "#9c8a90"
GREEN = "#5cd142"
RED = "#e05a5a"
AMBER = "#e0a94d"

STATUS_STYLE = {
    "Pending": ("clock", MUTED),
    "Running": ("refresh-cw", PINK_STRONG),
    "Completed": ("check-circle", GREEN),
    "Failed": ("x-circle", RED),
    "Missing": ("alert-triangle", AMBER),
}

# Feather Icons (MIT License) - https://github.com/feathericons/feather
_SVG_BODY = {
    "upload-cloud": (
        '<polyline points="16 16 12 12 8 16"/>'
        '<line x1="12" y1="12" x2="12" y2="21"/>'
        '<path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>'
        '<polyline points="16 16 12 12 8 16"/>'
    ),
    "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "file-text": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/>'
        '<polyline points="10 9 9 9 8 9"/>'
    ),
    "trash-2": (
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<line x1="10" y1="11" x2="10" y2="17"/>'
        '<line x1="14" y1="11" x2="14" y2="17"/>'
    ),
    "refresh-cw": (
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
    ),
    "check-circle": (
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
    ),
    "x-circle": (
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="15" y1="9" x2="9" y2="15"/>'
        '<line x1="9" y1="9" x2="15" y2="15"/>'
    ),
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "circle": '<circle cx="12" cy="12" r="10"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "alert-triangle": (
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
        '1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 '
        '2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 '
        '2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 '
        '2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
    ),
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "hash": '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>',
    "mouse-pointer": '<path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/><path d="M13 13l6 6"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "list": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>'
           '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
    "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "wifi": '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/>'
            '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>',
}

_ICON_CACHE = {}


def make_icon(name, size=18, color=MUTED, stroke=2.0):
    """Render a Feather-icon-style SVG glyph into a QIcon, cached by (name, size, color, stroke)."""
    key = (name, size, color, stroke)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round">{_SVG_BODY[name]}</svg>'
    )

    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pix)
    _ICON_CACHE[key] = icon
    return icon


def icon_label(name, size=18, color=MUTED, stroke=2.0):
    label = QLabel()
    label.setPixmap(make_icon(name, size, color, stroke).pixmap(size, size))
    label.setFixedSize(size, size)
    return label


def detect_tool_version(command, pattern=r"(\d+\.\d+\.\d+)"):
    """Returns (found, version_string). Never raises."""
    path = shutil.which(command)
    if not path:
        return False, "Not found"

    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        text = (result.stdout or "") + (result.stderr or "")
        match = re.search(pattern, text)
        return True, (match.group(1) if match else "installed")
    except Exception:
        return True, "installed"


class ConversionWorker(QThread):
    """Runs hcxpcapngtool across a batch of capture files using up to `threads`
    concurrent worker processes (ThreadPoolExecutor), emitting per-file signals."""

    log_signal = Signal(str)
    row_progress_signal = Signal(int, int)
    status_signal = Signal(int, str)
    finished_signal = Signal()

    def __init__(self, files, hcx_path=HCXPCAPNGTOOL, output_dir="", threads=DEFAULT_THREADS):
        super().__init__()
        self.files = files
        self.hcx_path = hcx_path or HCXPCAPNGTOOL
        self.output_dir = output_dir
        self.threads = max(1, threads)

    def _output_path(self, file):
        name = Path(file).with_suffix(".22000").name
        if self.output_dir:
            return str(Path(self.output_dir) / name)
        return str(Path(file).with_suffix(".22000"))

    def _convert_one(self, index, file):
        output = self._output_path(file)

        if not Path(file).is_file():
            self.log_signal.emit(f"[ERROR] File no longer exists: {file}")
            self.status_signal.emit(index, "Missing")
            self.row_progress_signal.emit(index, 0)
            return

        self.log_signal.emit(f"[INFO] Converting: {file}")
        self.status_signal.emit(index, "Running")
        self.row_progress_signal.emit(index, 10)

        command = [self.hcx_path, "-o", output, file]

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            if result.stderr.strip():
                self.log_signal.emit(f"[INFO] {result.stderr.strip()}")
            self.log_signal.emit(f"[SUCCESS] Generated: {output}")
            self.status_signal.emit(index, "Completed")
            self.row_progress_signal.emit(index, 100)
        except subprocess.CalledProcessError as e:
            detail = (e.stderr or e.stdout or str(e)).strip()
            self.log_signal.emit(f"[ERROR] {file}: {detail}")
            self.status_signal.emit(index, "Failed")
            self.row_progress_signal.emit(index, 0)
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {file}: {e}")
            self.status_signal.emit(index, "Failed")
            self.row_progress_signal.emit(index, 0)

    def run(self):
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            futures = {
                pool.submit(self._convert_one, index, file): index
                for index, file in enumerate(self.files)
            }
            for future in as_completed(futures):
                future.result()

        self.finished_signal.emit()


class SettingsDialog(QDialog):
    def __init__(self, parent, hcx_path, output_dir, low_resource, threads):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(440)

        form = QFormLayout(self)
        form.setSpacing(10)

        hcx_row = QHBoxLayout()
        self.hcx_edit = QLineEdit(hcx_path)
        self.hcx_edit.setPlaceholderText("hcxpcapngtool")
        hcx_browse = QPushButton("Browse")
        hcx_browse.clicked.connect(self._browse_hcx)
        hcx_row.addWidget(self.hcx_edit)
        hcx_row.addWidget(hcx_browse)
        form.addRow("hcxpcapngtool path:", hcx_row)

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(output_dir)
        self.out_edit.setPlaceholderText("Same folder as source file")
        out_browse = QPushButton("Browse")
        out_browse.clicked.connect(self._browse_out)
        out_row.addWidget(self.out_edit)
        out_row.addWidget(out_browse)
        form.addRow("Output directory:", out_row)

        self.threads_edit = QLineEdit(str(threads))
        form.addRow("Conversion threads:", self.threads_edit)

        self.low_resource_edit = QLineEdit("on" if low_resource else "off")
        self.low_resource_edit.setPlaceholderText("on / off")
        form.addRow("Low resource mode:", self.low_resource_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse_hcx(self):
        path, _ = QFileDialog.getOpenFileName(self, "Locate hcxpcapngtool")
        if path:
            self.hcx_edit.setText(path)

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.out_edit.setText(path)

    def values(self):
        try:
            threads = max(1, int(self.threads_edit.text().strip()))
        except ValueError:
            threads = DEFAULT_THREADS
        low_resource = self.low_resource_edit.text().strip().lower() in ("on", "true", "1", "yes")
        return self.hcx_edit.text().strip(), self.out_edit.text().strip(), threads, low_resource


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("About HashCatcher")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(56, 56)
        logo.setScaledContents(True)
        if LOGO_PATH.exists():
            logo.setPixmap(QPixmap(str(LOGO_PATH)))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo, alignment=Qt.AlignCenter)

        title = QLabel(f"HashCatcher v{APP_VERSION}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13pt;")
        layout.addWidget(title)

        desc = QLabel(
            "Offline wireless capture conversion for Hashcat.\n"
            "Converts .cap / .pcap / .pcapng into Hashcat 22000 hashes\n"
            "using hcxpcapngtool.\n\n"
            "For authorized security testing and educational use only."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class LogsDialog(QDialog):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setWindowTitle("Process Logs")
        self.resize(640, 420)

        layout = QVBoxLayout(self)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        view.setStyleSheet("font-family: Consolas, monospace; font-size: 9.5pt;")
        layout.addWidget(view)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


SIDEBAR_ITEMS = (
    ("home", "Dashboard", None, "dashboard"),
    ("file-text", "Convert", ".cap, .pcap, .pcapng", None),
    ("hash", "Generate", "Hashcat 22000", None),
    ("mouse-pointer", "Drag & Drop", "File Support", None),
    ("layers", "Batch", "Conversion", None),
    ("shield", "Offline", "Operation", None),
    ("settings", "Settings", "Application Settings", "settings"),
    ("list", "Logs", "Process Logs", "logs"),
    ("info", "About", "About HashCatcher", "about"),
)


class HashCatcher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.files = []
        self.worker = None
        self.log_text = ""

        self.settings = QSettings("HashCatcher", "HashCatcher")
        self.hcx_path = self.settings.value("hcx_path", HCXPCAPNGTOOL)
        self.output_dir = self.settings.value("output_dir", "") or str(Path.home() / "HashCatcher" / "output")
        self.threads = int(self.settings.value("threads", DEFAULT_THREADS))
        self.low_resource = str(self.settings.value("low_resource", "false")).lower() in ("true", "1")

        self.setWindowTitle("HashCatcher")
        self.resize(1536, 1024)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.setAcceptDrops(True)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(20)
        root.addLayout(body, 1)

        self.setup_sidebar(body)
        self.setup_main(body)

        self.setup_statusbar(root)

        self.apply_theme()
        self.refresh_system_info()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def setup_sidebar(self, layout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 14)
        sidebar_layout.setSpacing(16)

        logo = QLabel()
        logo.setFixedSize(72, 72)
        logo.setScaledContents(True)
        if LOGO_PATH.exists():
            logo.setPixmap(QPixmap(str(LOGO_PATH)))
        sidebar_layout.addWidget(logo, alignment=Qt.AlignHCenter)

        nav_block = QVBoxLayout()
        nav_block.setSpacing(6)
        for icon, title, subtitle, action in SIDEBAR_ITEMS:
            nav_block.addWidget(self._make_nav_item(icon, title, subtitle, action))
        sidebar_layout.addLayout(nav_block)

        sidebar_layout.addStretch(1)

        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(6)

        info_title = QLabel("System Info")
        info_title.setObjectName("infoCardTitle")
        info_layout.addWidget(info_title)

        self.hcx_info_row, self.hcx_info_label, self.hcx_info_icon = self._make_info_row("hcxtools")
        self.hashcat_info_row, self.hashcat_info_label, self.hashcat_info_icon = self._make_info_row("Hashcat")
        info_layout.addWidget(self.hcx_info_row)
        info_layout.addWidget(self.hashcat_info_row)
        sidebar_layout.addWidget(info_card)

        footer = QVBoxLayout()
        footer.setSpacing(0)
        version_label = QLabel(f"HashCatcher v{APP_VERSION}")
        version_label.setObjectName("sidebarFooter")
        copyright_label = QLabel("© 2026 Tahsasiyahu")
        copyright_label.setObjectName("sidebarFooter")
        footer.addWidget(version_label)
        footer.addWidget(copyright_label)
        sidebar_layout.addLayout(footer)

        layout.addWidget(sidebar)

    def _make_nav_item(self, icon, title, subtitle, action):
        btn = QToolButton()
        btn.setObjectName("navItemActive" if action == "dashboard" else "navItem")
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setIcon(make_icon(icon, 18, PINK if action == "dashboard" else "#b97a93", 2.0))
        btn.setIconSize(btn.iconSize())
        text = title if not subtitle else f"{title}\n{subtitle}"
        btn.setText(text.replace("&", "&&"))
        btn.setCursor(Qt.PointingHandCursor)
        if action:
            btn.clicked.connect(lambda _c=False, a=action: self.handle_nav(a))
        return btn

    def _make_info_row(self, label_text):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        label = QLabel(f"{label_text}: ...")
        label.setObjectName("infoCardText")
        icon = QLabel()
        row_layout.addWidget(label, 1)
        row_layout.addWidget(icon)
        return row, label, icon

    def handle_nav(self, action):
        if action == "settings":
            self.open_settings()
        elif action == "about":
            AboutDialog(self).exec()
        elif action == "logs":
            LogsDialog(self, self.log_text or "No activity yet.").exec()

    def open_settings(self):
        dialog = SettingsDialog(self, self.hcx_path, self.output_dir, self.low_resource, self.threads)
        if dialog.exec() == QDialog.Accepted:
            hcx_path, output_dir, threads, low_resource = dialog.values()
            self.hcx_path = hcx_path or HCXPCAPNGTOOL
            self.output_dir = output_dir
            self.threads = threads
            self.low_resource = low_resource
            self.settings.setValue("hcx_path", self.hcx_path)
            self.settings.setValue("output_dir", self.output_dir)
            self.settings.setValue("threads", self.threads)
            self.settings.setValue("low_resource", self.low_resource)
            self.output_dir_edit.setText(self.output_dir)
            self.refresh_system_info()
            self.update_footer_status()

    def refresh_system_info(self):
        hcx_found, hcx_version = detect_tool_version(self.hcx_path if Path(str(self.hcx_path)).is_absolute() else HCXPCAPNGTOOL)
        hashcat_found, hashcat_version = detect_tool_version(HASHCAT)

        self.hcx_info_label.setText(f"hcxtools: {hcx_version}")
        self.hcx_info_icon.setPixmap(
            make_icon("check-circle" if hcx_found else "x-circle", 14, GREEN if hcx_found else RED, 2.2).pixmap(14, 14)
        )
        self.hashcat_info_label.setText(f"Hashcat: {hashcat_version}")
        self.hashcat_info_icon.setPixmap(
            make_icon("check-circle" if hashcat_found else "x-circle", 14, GREEN if hashcat_found else RED, 2.2).pixmap(14, 14)
        )

    # ------------------------------------------------------------------
    # Main panel
    # ------------------------------------------------------------------
    def setup_main(self, layout):
        main_col = QVBoxLayout()
        main_col.setSpacing(16)

        self.setup_header(main_col)
        self.setup_drop_zone(main_col)
        self.setup_queue(main_col)
        self.setup_output_dir(main_col)
        self.setup_toolbar(main_col)

        layout.addLayout(main_col, 1)

    def setup_header(self, layout):
        header = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("HashCatcher")
        title.setObjectName("appTitle")
        title_font = QFont("Segoe UI", 26, QFont.Bold)
        title_font.setStyleHint(QFont.SansSerif)
        title.setFont(title_font)
        title_row.addWidget(title)

        badge = QLabel(f"v{APP_VERSION.rsplit('.', 1)[0]}")
        badge.setObjectName("versionBadge")
        title_row.addWidget(badge)
        title_row.addStretch(1)
        title_block.addLayout(title_row)

        subtitle = QLabel("Offline Wireless Capture Conversion for Hashcat 22000")
        subtitle.setObjectName("subtitle")
        title_block.addWidget(subtitle)

        header.addLayout(title_block, 1)

        self.ready_pill = QLabel()
        self.ready_pill.setObjectName("readyPill")
        header.addWidget(self.ready_pill, alignment=Qt.AlignTop)

        layout.addLayout(header)

    def setup_drop_zone(self, layout):
        drop = QFrame()
        drop.setObjectName("dropZone")

        drop_layout = QVBoxLayout(drop)
        drop_layout.setContentsMargins(20, 24, 20, 24)
        drop_layout.setSpacing(8)
        drop_layout.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setPixmap(make_icon("upload-cloud", 48, PINK, 1.8).pixmap(48, 48))
        icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(icon)

        hint = QLabel("Drag & drop capture files here")
        hint.setObjectName("dropZoneHint")
        hint.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(hint)

        sub_hint = QLabel("or click 'Browse Files' to select")
        sub_hint.setObjectName("dropZoneSubHint")
        sub_hint.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(sub_hint)

        self.add_btn = QPushButton(" Browse Files")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setIcon(make_icon("folder", 16, "#ffffff", 2.0))
        self.add_btn.clicked.connect(self.add_files)
        drop_layout.addWidget(self.add_btn, alignment=Qt.AlignCenter)

        layout.addWidget(drop)

    def setup_queue(self, layout):
        queue_header = QHBoxLayout()
        self.queue_title = QLabel("Conversion Queue (0)")
        self.queue_title.setObjectName("sectionTitle")
        queue_header.addWidget(self.queue_title)
        queue_header.addStretch(1)

        clear_completed_btn = QToolButton()
        clear_completed_btn.setObjectName("linkBtn")
        clear_completed_btn.setIcon(make_icon("trash-2", 14, PINK, 2.0))
        clear_completed_btn.setText(" Clear Completed")
        clear_completed_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        clear_completed_btn.setCursor(Qt.PointingHandCursor)
        clear_completed_btn.clicked.connect(self.clear_completed)
        queue_header.addWidget(clear_completed_btn)

        layout.addLayout(queue_header)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("queueTable")
        self.table.setHorizontalHeaderLabels(
            ["#", "File Name", "Type", "Size", "Status", "Progress", "Output"]
        )
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setShowGrid(False)

        self.table.setColumnWidth(0, 44)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 190)
        self.table.setColumnWidth(6, 230)

        layout.addWidget(self.table, 1)

    def setup_output_dir(self, layout):
        row = QHBoxLayout()
        label = QLabel("Output Directory")
        label.setObjectName("sectionTitle")
        layout.addWidget(label)

        field_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit(self.output_dir)
        self.output_dir_edit.setObjectName("outputDirField")
        self.output_dir_edit.setReadOnly(True)
        field_row.addWidget(self.output_dir_edit, 1)

        change_btn = QPushButton(" Change")
        change_btn.setObjectName("secondaryBtn")
        change_btn.setIcon(make_icon("folder", 16, "#e0c8d0", 2.0))
        change_btn.clicked.connect(self.change_output_dir)
        field_row.addWidget(change_btn)

        layout.addLayout(field_row)

    def change_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir)
        if path:
            self.output_dir = path
            self.output_dir_edit.setText(path)
            self.settings.setValue("output_dir", path)

    def setup_toolbar(self, layout):
        toolbar = QHBoxLayout()

        self.add_files_btn = QPushButton(" Add Files")
        self.add_files_btn.setObjectName("secondaryBtn")
        self.add_files_btn.setIcon(make_icon("plus", 16, "#e0c8d0", 2.0))
        self.add_files_btn.clicked.connect(self.add_files)

        self.remove_btn = QPushButton(" Remove Selected")
        self.remove_btn.setObjectName("secondaryBtn")
        self.remove_btn.setIcon(make_icon("trash-2", 16, "#e0c8d0", 2.0))
        self.remove_btn.clicked.connect(self.remove_selected)

        toolbar.addWidget(self.add_files_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addStretch(1)

        self.convert_btn = QPushButton(" Convert All")
        self.convert_btn.setObjectName("primaryBtnLarge")
        self.convert_btn.setIcon(make_icon("play", 16, "#ffffff", 2.0))
        self.convert_btn.clicked.connect(self.convert_files)
        toolbar.addWidget(self.convert_btn)

        layout.addLayout(toolbar)

    def setup_statusbar(self, layout):
        bar = QFrame()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(34)

        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(20, 0, 20, 0)

        self.low_res_label = QLabel()
        self.threads_label = QLabel()
        self.status_label = QLabel()

        for lbl in (self.low_res_label, self.threads_label, self.status_label):
            lbl.setObjectName("statusBarText")

        bar_layout.addWidget(self.low_res_label)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self.threads_label)
        bar_layout.addStretch(1)
        bar_layout.addWidget(self.status_label)

        layout.addWidget(bar)
        self.update_footer_status()

    def update_footer_status(self, state="Ready"):
        self.low_res_label.setText(f"Low Resource Mode: {'ON' if self.low_resource else 'OFF'}")
        effective_threads = 1 if self.low_resource else self.threads
        self.threads_label.setText(f"Threads: {effective_threads}")
        self.status_label.setText(f"Status: {state}")

        if hasattr(self, "ready_pill"):
            color = {"Ready": GREEN, "Converting": PINK_STRONG, "Error": RED}.get(state, MUTED)
            self.ready_pill.setText(f"● {state}")
            self.ready_pill.setStyleSheet(
                f"background-color: rgba(255,255,255,0.04); color: {color}; "
                f"border: 1px solid #2b1620; border-radius: 14px; padding: 6px 14px; font-weight: bold;"
            )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, #central {{ background-color: #0f0a0d; }}

            QWidget {{
                background-color: transparent;
                color: #f5f5f5;
                font-family: Segoe UI;
                font-size: 10.5pt;
            }}

            #sidebar {{ background-color: #150e11; border-right: 1px solid #241420; }}
            #appTitle {{ color: #ffffff; }}
            #versionBadge {{
                background-color: rgba(255,255,255,0.06);
                color: {GRAY_TEXT};
                border: 1px solid #3a222c;
                border-radius: 8px;
                padding: 2px 10px;
                font-weight: bold;
            }}
            #subtitle {{ color: {MUTED}; font-size: 10pt; }}

            QToolButton#navItem, QToolButton#navItemActive {{
                text-align: left;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                color: #d9b8c4;
                font-weight: bold;
            }}
            QToolButton#navItemActive {{ background-color: #7a1f42; color: #ffffff; }}
            QToolButton#navItem:hover {{ background-color: #231319; }}

            #infoCard {{ background-color: #241019; border: 1px solid #3a222c; border-radius: 10px; }}
            #infoCardTitle {{ color: {MUTED}; font-weight: bold; font-size: 9pt; }}
            #infoCardText {{ color: {GRAY_TEXT}; font-size: 9pt; }}
            #sidebarFooter {{ color: {MUTED}; font-size: 8pt; }}

            #dropZone {{ background-color: #1c1419; border: 2px dashed #4a3c42; border-radius: 12px; }}
            #dropZoneHint {{ color: #ffffff; font-weight: bold; font-size: 12pt; }}
            #dropZoneSubHint {{ color: {MUTED}; font-size: 9.5pt; }}

            #sectionTitle {{ color: {GRAY_TEXT}; font-weight: bold; }}

            QPushButton#primaryBtn {{
                background-color: #c2185b; border-radius: 10px; padding: 10px 20px; color: white; font-weight: bold;
            }}
            QPushButton#primaryBtn:hover {{ background-color: #ff4d7a; }}

            QPushButton#primaryBtnLarge {{
                background-color: #c2185b; border-radius: 10px; padding: 12px 28px; color: white; font-weight: bold; font-size: 11pt;
            }}
            QPushButton#primaryBtnLarge:hover {{ background-color: #ff4d7a; }}
            QPushButton#primaryBtnLarge:disabled {{ background-color: #5c2634; color: {MUTED}; }}

            QPushButton#secondaryBtn {{
                background-color: #1c1419; border: 1px solid #3a222c; border-radius: 10px; padding: 10px 16px; color: #e0c8d0; font-weight: bold;
            }}
            QPushButton#secondaryBtn:hover {{ background-color: #241019; }}
            QPushButton#secondaryBtn:disabled {{ color: #6a5a60; }}

            QToolButton#linkBtn {{ background-color: transparent; border: none; color: {PINK}; font-weight: bold; }}
            QToolButton#linkBtn:hover {{ color: {PINK_STRONG}; }}

            QLineEdit#outputDirField {{
                background-color: #140b10; border: 1px solid #2b1620; border-radius: 10px; padding: 8px 12px; color: {GRAY_TEXT};
            }}

            QTableWidget#queueTable {{ background-color: #140b10; border: 1px solid #2b1620; border-radius: 10px; }}
            QTableWidget#queueTable::item {{ border-bottom: 1px solid #241420; }}
            QTableWidget#queueTable::item:selected {{ background-color: rgba(194,24,91,0.15); }}
            QHeaderView::section {{
                background-color: #1c141a; color: {GRAY_TEXT}; border: none; border-bottom: 1px solid #2b1620;
                padding: 8px 6px; font-weight: bold;
            }}

            #rowIndex {{ color: {MUTED}; }}
            #rowFileName {{ color: #f5f5f5; font-weight: bold; }}
            #typePill {{
                background-color: rgba(194,24,91,0.15); color: #ff9fb8; border: 1px solid rgba(194,24,91,0.4); border-radius: 11px;
                padding: 2px 12px; font-size: 8.5pt; font-weight: bold;
            }}
            #rowOutput {{ color: #c9b8bf; font-size: 9pt; }}
            #rowProgressText {{ color: {MUTED}; font-size: 8.5pt; }}

            QToolButton#openFolderBtn {{ background-color: transparent; border: none; border-radius: 6px; padding: 4px; }}
            QToolButton#openFolderBtn:hover {{ background-color: #241019; }}

            QProgressBar#rowProgress {{ border-radius: 4px; background-color: #241019; height: 6px; }}
            QProgressBar#rowProgress::chunk {{ background-color: {GREEN}; border-radius: 4px; }}

            #statusBar {{ background-color: #0a0609; border-top: 1px solid #241420; }}
            #statusBarText {{ color: {MUTED}; font-size: 8.5pt; }}
        """)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def add_log(self, message):
        self.log_text += message + "\n"

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

        self._update_queue_title()

    def add_file_to_table(self, file):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 54)

        file_path = Path(file)

        index_item = QTableWidgetItem(str(row + 1))
        index_item.setTextAlignment(Qt.AlignCenter)
        index_item.setForeground(Qt.gray)
        self.table.setItem(row, 0, index_item)

        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(8, 4, 4, 4)
        file_layout.setSpacing(8)
        file_layout.addWidget(icon_label("file-text", 18, GRAY_TEXT, 2.0))
        name_label = QLabel(file_path.name)
        name_label.setObjectName("rowFileName")
        name_label.setToolTip(str(file_path))
        file_layout.addWidget(name_label, 1)
        self.table.setCellWidget(row, 1, file_widget)

        type_wrap = QWidget()
        type_wrap_layout = QHBoxLayout(type_wrap)
        type_wrap_layout.setContentsMargins(8, 0, 0, 0)
        type_label = QLabel(file_path.suffix.lstrip(".").upper())
        type_label.setObjectName("typePill")
        type_label.setAlignment(Qt.AlignCenter)
        type_wrap_layout.addWidget(type_label)
        type_wrap_layout.addStretch(1)
        self.table.setCellWidget(row, 2, type_wrap)

        try:
            size = round(file_path.stat().st_size / 1024 / 1024, 1)
            size_text = f"{size} MB"
        except OSError:
            size_text = "N/A"
        size_item = QTableWidgetItem(size_text)
        size_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, 3, size_item)

        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 0, 0, 0)
        status_layout.setSpacing(6)
        status_layout.addWidget(QLabel())
        status_layout.addWidget(QLabel())
        status_layout.addStretch(1)
        self.table.setCellWidget(row, 4, status_widget)
        self._apply_status(status_widget, "Pending")

        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(8, 0, 8, 0)
        progress_layout.setSpacing(8)
        progress_text = QLabel("0%")
        progress_text.setObjectName("rowProgressText")
        progress_text.setFixedWidth(30)
        progress_bar = QProgressBar()
        progress_bar.setObjectName("rowProgress")
        progress_bar.setTextVisible(False)
        progress_bar.setValue(0)
        progress_layout.addWidget(progress_text)
        progress_layout.addWidget(progress_bar, 1)
        self.table.setCellWidget(row, 5, progress_widget)

        output_path = file_path.with_suffix(".22000")
        if self.output_dir:
            output_path = Path(self.output_dir) / output_path.name

        out_widget = QWidget()
        out_layout = QHBoxLayout(out_widget)
        out_layout.setContentsMargins(6, 4, 6, 4)
        out_layout.setSpacing(6)
        out_label = QLabel(output_path.name)
        out_label.setObjectName("rowOutput")
        out_layout.addWidget(out_label, 1)

        open_btn = QToolButton()
        open_btn.setObjectName("openFolderBtn")
        open_btn.setIcon(make_icon("folder", 16, MUTED, 2.0))
        open_btn.setToolTip("Open containing folder")
        open_btn.clicked.connect(
            lambda _checked=False, p=output_path: self.open_output_folder(p)
        )
        out_layout.addWidget(open_btn)
        self.table.setCellWidget(row, 6, out_widget)

    def _apply_status(self, widget, status):
        name, color = STATUS_STYLE.get(status, ("clock", MUTED))
        icon_lbl = widget.layout().itemAt(0).widget()
        text_lbl = widget.layout().itemAt(1).widget()
        icon_lbl.setPixmap(make_icon(name, 14, color, 2.4).pixmap(14, 14))
        text_lbl.setText(status)
        text_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 9.5pt;")

    def _set_row_progress(self, row, value):
        widget = self.table.cellWidget(row, 5)
        if widget is None:
            return
        text_lbl = widget.layout().itemAt(0).widget()
        bar = widget.layout().itemAt(1).widget()
        text_lbl.setText(f"{value}%")
        bar.setValue(value)

    def open_output_folder(self, path):
        folder = Path(path).parent
        if folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            QMessageBox.information(self, "Folder Not Found", f"{folder} does not exist yet.")

    def _update_queue_title(self):
        self.queue_title.setText(f"Conversion Queue ({len(self.files)})")

    def _row_status_text(self, row):
        widget = self.table.cellWidget(row, 4)
        return widget.layout().itemAt(1).widget().text()

    def clear_completed(self):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "Conversion Running", "Please wait for the current conversion to finish.")
            return

        keep_rows = [r for r in range(self.table.rowCount()) if self._row_status_text(r) != "Completed"]
        self._rebuild_from_rows(keep_rows)

    def remove_selected(self):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "Conversion Running", "Please wait for the current conversion to finish.")
            return

        selected = {idx.row() for idx in self.table.selectionModel().selectedRows()}
        if not selected:
            return
        keep_rows = [r for r in range(self.table.rowCount()) if r not in selected]
        self._rebuild_from_rows(keep_rows)

    def _rebuild_from_rows(self, keep_rows):
        remaining_files = [self.files[r] for r in keep_rows]
        self.files = []
        self.table.setRowCount(0)
        for file in remaining_files:
            self.files.append(file)
            self.add_file_to_table(file)
        self._update_queue_title()

    def convert_files(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add capture files.")
            return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Conversion Running", "A conversion is already in progress.")
            return

        if not self.check_hcxtools():
            QMessageBox.critical(
                self,
                "hcxtools Missing",
                "hcxpcapngtool was not found.\n\nInstall hcxtools, or set a custom path in Settings.",
            )
            return

        self.set_controls_enabled(False)
        self.update_footer_status("Converting")

        try:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        effective_threads = 1 if self.low_resource else self.threads
        self.worker = ConversionWorker(list(self.files), self.hcx_path, self.output_dir, effective_threads)

        self.worker.log_signal.connect(self.add_log)
        self.worker.row_progress_signal.connect(self._set_row_progress)
        self.worker.status_signal.connect(self.update_status)
        self.worker.finished_signal.connect(self.on_conversion_finished)

        self.worker.start()

    def on_conversion_finished(self):
        self.set_controls_enabled(True)
        failed = any(self._row_status_text(r) not in ("Completed",) for r in range(self.table.rowCount()))
        self.update_footer_status("Error" if failed else "Ready")
        self.add_log("[INFO] Conversion batch finished.")

    def set_controls_enabled(self, enabled):
        self.add_btn.setEnabled(enabled)
        self.add_files_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)

    def update_status(self, row, status):
        widget = self.table.cellWidget(row, 4)
        if widget is not None:
            self._apply_status(widget, status)

    def check_hcxtools(self):
        path = self.hcx_path or HCXPCAPNGTOOL
        if Path(str(path)).is_absolute():
            return Path(path).is_file()
        return shutil.which(path) is not None

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

        self._update_queue_title()


if __name__ == "__main__":
    QApplication.setStyle("Fusion")

    app = QApplication(sys.argv)

    window = HashCatcher()
    window.show()

    sys.exit(app.exec())
