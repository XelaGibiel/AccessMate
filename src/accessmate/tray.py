"""System tray icon and context menu.

The tray menu is rebuilt dynamically whenever modules are enabled or disabled,
so it always stays compact and only shows what the user has activated.

Icon colors:
- Blue  (#1565C0) – normal, at least one module active
- Grey  (#616161) – running but no modules active
- Red   (#C62828) – paused (emergency stop or pause-all)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from accessmate.core.event_bus import bus
from accessmate.core.i18n import tr

if TYPE_CHECKING:
    from accessmate.app import AccessMateApp

ICON_PATH = Path(__file__).parent.parent.parent / "assets" / "icons" / "accessmate.ico"


def _make_icon(color: str) -> QIcon:
    """Generate an 'AM' tray icon in the given hex color."""
    px = QPixmap(32, 32)
    px.fill(QColor(color))
    painter = QPainter(px)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(13)
    painter.setFont(font)
    painter.drawText(
        px.rect(),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "AM",
    )
    painter.end()
    return QIcon(px)


_ICON_ACTIVE  = _make_icon("#1565C0")  # blue  – modules running
_ICON_IDLE    = _make_icon("#616161")  # grey  – no modules active
_ICON_PAUSED  = _make_icon("#C62828")  # red   – paused / emergency stop


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app: "AccessMateApp") -> None:
        icon = QIcon(str(ICON_PATH)) if ICON_PATH.exists() else _ICON_IDLE
        super().__init__(icon)
        self._app = app
        self.setToolTip(tr("app.name"))
        self._build_menu()

        bus.subscribe("module.started",          lambda **_: self._refresh())
        bus.subscribe("module.stopped",          lambda **_: self._refresh())
        bus.subscribe("app.paused",              lambda **_: self._set_paused(True))
        bus.subscribe("app.resumed",             lambda **_: self._set_paused(False))
        bus.subscribe("i18n.language_changed",   lambda **_: self._refresh())

        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------
    # Icon state
    # ------------------------------------------------------------------

    def _set_paused(self, paused: bool) -> None:
        if paused:
            self.setIcon(_ICON_PAUSED)
            self.setToolTip(f"{tr('app.name')} – {tr('app.pause_all')}")
        else:
            self._update_icon()
            self.setToolTip(tr("app.name"))
        self._build_menu()

    def _update_icon(self) -> None:
        if ICON_PATH.exists():
            self.setIcon(QIcon(str(ICON_PATH)))
            return
        any_active = any(m.enabled for m in self._app.get_modules())
        self.setIcon(_ICON_ACTIVE if any_active else _ICON_IDLE)

    def _refresh(self) -> None:
        self._update_icon()
        self._build_menu()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        menu.addAction(tr("tray.open_settings"), self._app.show_settings)
        menu.addSeparator()

        for module in self._app.get_modules():
            prefix = tr("tray.module_active_prefix") if module.enabled else "   "
            menu.addAction(f"{prefix}{module.DISPLAY_NAME}", module.toggle)

        menu.addSeparator()

        profile_menu = menu.addMenu(tr("tray.switch_profile"))
        for profile_name in self._app.list_profiles():
            action = profile_menu.addAction(
                profile_name,
                lambda name=profile_name: self._app.switch_profile(name),
            )
            action.setCheckable(True)
            action.setChecked(profile_name == self._app.active_profile)

        menu.addSeparator()

        if self._app._paused:
            menu.addAction(tr("app.resume_all"), self._app.resume_all)
        else:
            menu.addAction(tr("app.pause_all"), self._app.pause_all)

        menu.addSeparator()
        menu.addAction(tr("app.quit"), self._app.quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._app.show_settings()
