"""Entry point for AccessMate.

Run with:
    python -m accessmate
or after installation:
    accessmate
"""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from accessmate.app import AccessMateApp

_MUTEX_NAME = "Global\\AccessMate_SingleInstance"


def _acquire_single_instance_mutex() -> object | None:
    """Create a named Windows mutex to prevent multiple instances.

    Returns the mutex handle if this is the first instance, or None if
    AccessMate is already running.
    """
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()

    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex


def main() -> None:
    mutex = _acquire_single_instance_mutex()

    if mutex is None:
        # Another instance is already running – show a brief notice and exit.
        # QApplication is needed to show the message box.
        app = QApplication(sys.argv)
        app.setApplicationName("AccessMate")
        QMessageBox.information(
            None,
            "AccessMate",
            "AccessMate läuft bereits im Hintergrund.\n"
            "Du findest es im Systemtray (unten rechts).",
        )
        sys.exit(0)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("AccessMate")
    qt_app.setApplicationVersion("0.1.0")
    qt_app.setQuitOnLastWindowClosed(False)

    _app = AccessMateApp(qt_app)

    exit_code = qt_app.exec()

    # Release the mutex when the app exits cleanly.
    ctypes.windll.kernel32.ReleaseMutex(mutex)
    ctypes.windll.kernel32.CloseHandle(mutex)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
