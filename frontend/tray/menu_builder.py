from PySide6.QtWidgets import QMenu

def build_tray_menu(actions: dict[str, QMenu]) -> QMenu:
    menu = QMenu()
    
    menu.addAction(actions["show"])
    menu.addSeparator()
    menu.addAction(actions["quit"])
    return menu