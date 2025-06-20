import sys
import os
import json
import subprocess
import webbrowser
import shutil
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
                             QLineEdit, QLabel, QDialog, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint

SHORTCUTS_FILE = 'shortcuts.json'
ICONS_DIR = 'icons'
DEFAULT_ICON = os.path.join(ICONS_DIR, 'default.png')

if not os.path.exists(ICONS_DIR):
    os.makedirs(ICONS_DIR)

if not os.path.exists(DEFAULT_ICON):
    app = QApplication(sys.argv)
    default_icon = QPixmap(32, 32)
    default_icon.fill(QColor(200, 200, 200))
    default_icon.save(DEFAULT_ICON)
    del app

class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Shortcut")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter name")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter app path or URL")
        self.icon_path = DEFAULT_ICON

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)

        icon_button = QPushButton("Choose Icon")
        icon_button.clicked.connect(self.choose_icon)

        add_button = QPushButton("Add")
        add_button.clicked.connect(self.on_add)

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Path or URL:"))
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        layout.addWidget(icon_button)
        layout.addWidget(add_button)
        self.setLayout(layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.path_input.setText(file_path)

    def choose_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(self, "Choose Icon", filter="Images (*.png *.jpg *.bmp)")
        if icon_path:
            new_icon_path = os.path.join(ICONS_DIR, os.path.basename(icon_path))
            shutil.copyfile(icon_path, new_icon_path)
            self.icon_path = new_icon_path

    def get_data(self):
        return self.name_input.text(), self.path_input.text(), self.icon_path

    def on_add(self):
        if self.name_input.text() and self.path_input.text():
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Both name and path/URL are required.")

class ShortcutPanel(QWidget):
    def __init__(self, shortcuts, parent):
        super().__init__()
        self.shortcuts = shortcuts
        self.parent = parent
        self.setWindowFlags(Qt.Popup)
        self.setFixedWidth(250)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.refresh_ui()

    def refresh_ui(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                while item.count():
                    sub = item.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        for i, item in enumerate(self.shortcuts):
            row = QHBoxLayout()

            icon = QIcon(item.get('icon', DEFAULT_ICON))
            btn = QPushButton(icon, item['name'])
            btn.clicked.connect(lambda _, path=item['path']: self.launch_item(path))

            up_btn = QPushButton("↑")
            up_btn.clicked.connect(lambda _, idx=i: self.move_up(idx))
            down_btn = QPushButton("↓")
            down_btn.clicked.connect(lambda _, idx=i: self.move_down(idx))
            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, idx=i: self.delete_shortcut(idx))

            row.addWidget(btn)
            row.addWidget(up_btn)
            row.addWidget(down_btn)
            row.addWidget(del_btn)
            self.layout.addLayout(row)

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.add_shortcut)
        self.layout.addWidget(add_btn)

    def launch_item(self, path):
        if path.startswith("http"):
            webbrowser.open(path)
        else:
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open {path}:\n{e}")
        self.close()

    def add_shortcut(self):
        dialog = ShortcutDialog(self)
        if dialog.exec_():
            name, path, icon = dialog.get_data()
            if name and path:
                self.shortcuts.append({'name': name, 'path': path, 'icon': icon})
                self.save_and_refresh()

    def move_up(self, index):
        if index > 0:
            self.shortcuts[index - 1], self.shortcuts[index] = self.shortcuts[index], self.shortcuts[index - 1]
            self.save_and_refresh()

    def move_down(self, index):
        if index < len(self.shortcuts) - 1:
            self.shortcuts[index + 1], self.shortcuts[index] = self.shortcuts[index], self.shortcuts[index + 1]
            self.save_and_refresh()

    def delete_shortcut(self, index):
        del self.shortcuts[index]
        self.save_and_refresh()

    def save_and_refresh(self):
        with open(SHORTCUTS_FILE, 'w') as file:
            json.dump(self.shortcuts, file)
        self.refresh_ui()

class QuickBall(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick Ball")
        self.setFixedSize(80, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(50, 50)

        self.dragging = False
        self.panel_open = False
        self.panel = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 122, 204, 200))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            event.accept()
        else:
            self.show_shortcuts()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_shortcuts()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        pass  # Disabled double click functionality

    def show_shortcuts(self):
        if not os.path.exists(SHORTCUTS_FILE):
            shortcuts = []
        else:
            try:
                with open(SHORTCUTS_FILE, 'r') as file:
                    shortcuts = json.load(file)
            except json.JSONDecodeError:
                shortcuts = []

        if self.panel:
            self.panel.close()

        self.panel = ShortcutPanel(shortcuts, self)
        self.panel.move(self.x() + self.width(), self.y())
        self.panel.show()
        self.panel_open = True

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QuickBall()
    window.show()
    sys.exit(app.exec_())