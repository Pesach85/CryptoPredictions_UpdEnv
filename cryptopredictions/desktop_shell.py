"""Native desktop shell (PySide6) — Windows & Linux.

Not a browser wrapper: Qt widgets call live Python services directly
(Volatility radar, asset list, API hub). Optional Streamlit Lab opens
in the system browser as a secondary research surface.
"""

from __future__ import annotations

import json
import sys
import traceback
import webbrowser
from typing import Any

from cryptopredictions.paths import (
    ensure_sys_path,
    load_config,
    platform_name,
)
from cryptopredictions.runtime import RuntimeHub


def _require_qt():
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QAction, QIcon
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QStatusBar,
            QSystemTrayIcon,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise ImportError(
            "PySide6 is required for the native desktop shell. "
            "Install with: pip install PySide6"
        ) from exc
    return {
        "Qt": Qt,
        "QTimer": QTimer,
        "QAction": QAction,
        "QIcon": QIcon,
        "QApplication": QApplication,
        "QComboBox": QComboBox,
        "QFormLayout": QFormLayout,
        "QGroupBox": QGroupBox,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QMainWindow": QMainWindow,
        "QMessageBox": QMessageBox,
        "QPushButton": QPushButton,
        "QSpinBox": QSpinBox,
        "QStatusBar": QStatusBar,
        "QSystemTrayIcon": QSystemTrayIcon,
        "QTabWidget": QTabWidget,
        "QTextEdit": QTextEdit,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
    }


DISCLAIMER = "Simulation only — not investment advice."


class MainWindow:
    def __init__(self, qt: dict, hub: RuntimeHub):
        self.qt = qt
        self.hub = hub
        QMainWindow = qt["QMainWindow"]
        self.win = QMainWindow()
        self.win.setWindowTitle("CryptoPredictions")
        self.win.resize(920, 640)
        self._build_ui()
        self._build_menu()
        self._build_tray()
        self._refresh_status()

    def _build_ui(self) -> None:
        qt = self.qt
        central = qt["QWidget"]()
        layout = qt["QVBoxLayout"](central)

        banner = qt["QLabel"](DISCLAIMER)
        banner.setWordWrap(True)
        layout.addWidget(banner)

        info = qt["QLabel"](
            f"Mode: <b>{self.hub.config.mode}</b> · Platform: <b>{platform_name()}</b><br>"
            f"Repo (live): <code>{self.hub.repo_root}</code>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        tabs = qt["QTabWidget"]()
        tabs.addTab(self._tab_home(), "Home")
        tabs.addTab(self._tab_volatility(), "Volatility radar")
        tabs.addTab(self._tab_services(), "Services")
        layout.addWidget(tabs)

        self.status = qt["QStatusBar"]()
        self.win.setStatusBar(self.status)
        self.win.setCentralWidget(central)

    def _tab_home(self) -> Any:
        qt = self.qt
        w = qt["QWidget"]()
        v = qt["QVBoxLayout"](w)
        v.addWidget(
            qt["QLabel"](
                "Native desktop shell. Volatility forecasts run in-process against the "
                "live codebase (dev-linked). Projection Lab (Streamlit) is optional."
            )
        )
        row = qt["QHBoxLayout"]()
        btn_api = qt["QPushButton"]("Start API")
        btn_api.clicked.connect(self._start_api)
        btn_lab = qt["QPushButton"]("Open Projection Lab")
        btn_lab.clicked.connect(self._open_lab)
        btn_docs = qt["QPushButton"]("Open API docs")
        btn_docs.clicked.connect(self._open_docs)
        row.addWidget(btn_api)
        row.addWidget(btn_lab)
        row.addWidget(btn_docs)
        v.addLayout(row)
        self.home_log = qt["QTextEdit"]()
        self.home_log.setReadOnly(True)
        v.addWidget(self.home_log)
        return w

    def _tab_volatility(self) -> Any:
        qt = self.qt
        w = qt["QWidget"]()
        form = qt["QFormLayout"](w)

        self.asset_combo = qt["QComboBox"]()
        try:
            ensure_sys_path(self.hub.repo_root)
            from services.projection import ProjectionService

            assets = ProjectionService().list_assets()
        except Exception:
            assets = ["ETHUSD", "XBTUSD", "SOLUSD"]
        self.asset_combo.addItems(assets)
        if "ETHUSD" in assets:
            self.asset_combo.setCurrentText("ETHUSD")

        self.threshold_spin = qt["QSpinBox"]()
        self.threshold_spin.setRange(5, 25)
        self.threshold_spin.setValue(10)
        self.threshold_spin.setSuffix(" %")

        run_btn = qt["QPushButton"]("Analyze volatility event")
        run_btn.clicked.connect(self._run_volatility)

        self.vol_out = qt["QTextEdit"]()
        self.vol_out.setReadOnly(True)

        form.addRow("Asset", self.asset_combo)
        form.addRow("Threshold", self.threshold_spin)
        form.addRow(run_btn)
        form.addRow(self.vol_out)
        return w

    def _tab_services(self) -> Any:
        qt = self.qt
        w = qt["QWidget"]()
        v = qt["QVBoxLayout"](w)
        self.svc_label = qt["QLabel"]("…")
        v.addWidget(self.svc_label)
        refresh = qt["QPushButton"]("Refresh status")
        refresh.clicked.connect(self._refresh_status)
        stop = qt["QPushButton"]("Stop managed services")
        stop.clicked.connect(self._stop_services)
        v.addWidget(refresh)
        v.addWidget(stop)
        v.addStretch(1)
        return w

    def _build_menu(self) -> None:
        qt = self.qt
        menu = self.win.menuBar()
        file_m = menu.addMenu("&File")
        act_quit = qt["QAction"]("Quit", self.win)
        act_quit.triggered.connect(self._quit)
        file_m.addAction(act_quit)

        tools = menu.addMenu("&Tools")
        act_api = qt["QAction"]("Start API", self.win)
        act_api.triggered.connect(self._start_api)
        tools.addAction(act_api)
        act_lab = qt["QAction"]("Projection Lab", self.win)
        act_lab.triggered.connect(self._open_lab)
        tools.addAction(act_lab)

        help_m = menu.addMenu("&Help")
        act_about = qt["QAction"]("About", self.win)
        act_about.triggered.connect(self._about)
        help_m.addAction(act_about)

    def _build_tray(self) -> None:
        qt = self.qt
        if not qt["QSystemTrayIcon"].isSystemTrayAvailable():
            return
        self.tray = qt["QSystemTrayIcon"](self.win)
        self.tray.setToolTip("CryptoPredictions")
        # Icon may be empty until packaging/icons exist — Qt still shows tray
        menu = self.win.findChild(type(self.win.menuBar()))  # noqa — build dedicated
        from PySide6.QtWidgets import QMenu

        tray_menu = QMenu()
        show = qt["QAction"]("Show", self.win)
        show.triggered.connect(self.win.showNormal)
        tray_menu.addAction(show)
        quit_a = qt["QAction"]("Quit", self.win)
        quit_a.triggered.connect(self._quit)
        tray_menu.addAction(quit_a)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(lambda *_: self.win.showNormal())
        self.tray.show()

    def _log(self, msg: str) -> None:
        self.home_log.append(msg)
        self.status.showMessage(msg, 5000)

    def _start_api(self) -> None:
        try:
            proc = self.hub.start_api()
            self._log(f"API ready: {proc.url}")
            self._linux_notify("API started", proc.url or "")
        except Exception as exc:
            self._error(str(exc))
        self._refresh_status()

    def _open_lab(self) -> None:
        try:
            if self.hub.config.auto_start_api:
                self.hub.start_api()
            lab = self.hub.start_streamlit()
            if lab.url:
                webbrowser.open(lab.url)
            self._log(f"Projection Lab: {lab.url}")
        except Exception as exc:
            self._error(str(exc))
        self._refresh_status()

    def _open_docs(self) -> None:
        try:
            api = self.hub.start_api()
            webbrowser.open(f"{api.url}/docs")
        except Exception as exc:
            self._error(str(exc))

    def _run_volatility(self) -> None:
        ensure_sys_path(self.hub.repo_root)
        asset = self.asset_combo.currentText()
        thr = float(self.threshold_spin.value())
        try:
            from services.volatility_events import VolatilityEventService

            result = VolatilityEventService().forecast(asset, threshold_pct=thr)
            payload = result.to_dict()
            self.vol_out.setPlainText(json.dumps(payload, indent=2))
            window = payload.get("most_probable_window", "")
            self._log(f"{asset}: P14={payload['probabilities']['14d_pct']}% · {window}")
            self._linux_notify(
                f"{asset} volatility",
                f"P14={payload['probabilities']['14d_pct']}% bias={payload['direction_bias']}",
            )
        except Exception as exc:
            self.vol_out.setPlainText(traceback.format_exc())
            self._error(str(exc))

    def _refresh_status(self) -> None:
        st = self.hub.status()
        self.svc_label.setText(
            f"<pre>{json.dumps(st, indent=2)}</pre>"
        )

    def _stop_services(self) -> None:
        self.hub.stop_all()
        self._log("Stopped managed services")
        self._refresh_status()

    def _linux_notify(self, title: str, body: str) -> None:
        if platform_name() == "linux":
            try:
                from cryptopredictions.platform_linux import notify

                notify(title, body)
            except Exception:
                pass

    def _about(self) -> None:
        from cryptopredictions import __version__

        self.qt["QMessageBox"].information(
            self.win,
            "About",
            f"CryptoPredictions {__version__}\n{DISCLAIMER}\n\n"
            f"Live repo: {self.hub.repo_root}",
        )

    def _error(self, msg: str) -> None:
        self.qt["QMessageBox"].critical(self.win, "Error", msg)

    def _quit(self) -> None:
        self.hub.stop_all()
        self.qt["QApplication"].instance().quit()

    def show(self) -> None:
        self.win.show()


def run_desktop() -> int:
    ensure_sys_path()
    cfg = load_config()
    hub = RuntimeHub.from_config(cfg)
    if cfg.auto_start_api:
        try:
            hub.start_api()
        except Exception:
            pass

    qt = _require_qt()
    app = qt["QApplication"](sys.argv)
    app.setApplicationName("CryptoPredictions")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(qt, hub)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_desktop())
