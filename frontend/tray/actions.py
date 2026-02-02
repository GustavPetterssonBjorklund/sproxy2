from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

def create_tray_actions(deps) -> dict[str, QAction]:
    actions = {}
    
    # Show main window
    def show_main_window():
        deps.main_window.show()
        deps.main_window.raise_()
        deps.main_window.activateWindow()
    
    actions["show"] = QAction("Show")
    actions["show"].triggered.connect(show_main_window)
    
    # Hide main window to tray
    def hide_main_window():
        deps.main_window.hide()
        if hasattr(deps, "tray_show_message"):
            deps.tray_show_message(
                "SProxy2",
                "Still running in the background. Use the tray menu to quit.",
            )
    
    # Exit application
    actions["quit"] = QAction("Quit")
    actions["quit"].triggered.connect(QApplication.quit)
    
    return actions