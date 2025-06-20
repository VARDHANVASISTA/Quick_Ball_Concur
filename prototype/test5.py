import sys
import os
import json
import subprocess
import webbrowser
import shutil
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
                             QLineEdit, QLabel, QDialog, QHBoxLayout, QMessageBox, QListWidget,
                             QListWidgetItem, QAbstractItemView, QMenu)
from PyQt5.QtGui import QPainter, QColor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer

SHORTCUTS_FILE = 'shortcuts.json'
ICONS_DIR = 'icons'
DEFAULT_ICON = os.path.join(ICONS_DIR, 'default.png')

# Ensure icons directory and default icon
def ensure_default_icon():
    if not os.path.exists(ICONS_DIR):
        os.makedirs(ICONS_DIR)
    if not os.path.exists(DEFAULT_ICON):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(180, 180, 180))
        pixmap.save(DEFAULT_ICON)

class ShortcutDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut")
        self.setFixedSize(300, 200)
        self.icon_path = data['icon'] if data else DEFAULT_ICON

        self.name_input = QLineEdit(data['name'] if data else "")
        self.path_input = QLineEdit(data['path'] if data else "")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)

        icon_button = QPushButton("Choose Icon")
        icon_button.clicked.connect(self.choose_icon)

        add_button = QPushButton("Save")
        add_button.clicked.connect(self.accept_data)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Path or URL:"))

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_input)
        path_row.addWidget(browse_button)
        layout.addLayout(path_row)

        layout.addWidget(icon_button)
        layout.addWidget(add_button)
        self.setLayout(layout)

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.path_input.setText(file)

    def choose_icon(self):
        file, _ = QFileDialog.getOpenFileName(self, "Choose Icon", filter="Images (*.png *.jpg *.bmp)")
        if file:
            dest = os.path.join(ICONS_DIR, os.path.basename(file))
            shutil.copyfile(file, dest)
            self.icon_path = dest

    def accept_data(self):
        if not self.name_input.text() or not self.path_input.text():
            QMessageBox.warning(self, "Missing Info", "Both name and path are required.")
            return
        self.accept()

    def get_data(self):
        return self.name_input.text(), self.path_input.text(), self.icon_path

class ShortcutPanel(QWidget):
    def __init__(self, shortcuts, parent_ball):
        super().__init__()
        self.shortcuts = shortcuts
        self.parent_ball = parent_ball
        self.setWindowFlags(Qt.Popup)
        self.setFixedWidth(300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setSpacing(5)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self.launch_item)

        self.layout.addWidget(self.list_widget)

        add_btn = QPushButton("+ Add Shortcut")
        add_btn.clicked.connect(self.add_shortcut)
        self.layout.addWidget(add_btn)

        self.populate_list()
        self.list_widget.model().rowsMoved.connect(self.save_reordered)

    def populate_list(self):
        self.list_widget.clear()
        for s in self.shortcuts:
            item = QListWidgetItem(QIcon(s.get('icon', DEFAULT_ICON)), s['name'])
            item.setData(Qt.UserRole, s)
            self.list_widget.addItem(item)

    def save_reordered(self):
        self.shortcuts = [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]
        self.save()

    def add_shortcut(self):
        dialog = ShortcutDialog(self)
        if dialog.exec_():
            name, path, icon = dialog.get_data()
            self.shortcuts.append({'name': name, 'path': path, 'icon': icon})
            self.save()
            self.populate_list()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.list_widget.mapToGlobal(pos))

        if action == edit_action:
            self.edit_shortcut(item)
        elif action == delete_action:
            self.delete_shortcut(item)

    def edit_shortcut(self, item):
        data = item.data(Qt.UserRole)
        dialog = ShortcutDialog(self, data)
        if dialog.exec_():
            name, path, icon = dialog.get_data()
            data.update({'name': name, 'path': path, 'icon': icon})
            self.save()
            self.populate_list()

    def delete_shortcut(self, item):
        self.shortcuts.remove(item.data(Qt.UserRole))
        self.save()
        self.populate_list()

    def save(self):
        with open(SHORTCUTS_FILE, 'w') as f:
            json.dump(self.shortcuts, f, indent=2)

    def launch_item(self, item):
        data = item.data(Qt.UserRole)
        try:
            if data['path'].startswith("http"):
                webbrowser.open(data['path'])
            else:
                os.startfile(data['path'])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self.close()

class ExitZone(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exit Zone")
        self.setFixedSize(80, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 0, 0, 180))
        painter.setPen(Qt.white)
        painter.drawEllipse(0, 0, self.width(), self.height())
        painter.drawText(self.rect(), Qt.AlignCenter, "X")

class QuickBall(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick Ball")
        self.setFixedSize(80, 80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(100, 100)

        self.dragging = False
        self.drag_start_pos = None
        self.panel = None

        self.exit_zone = ExitZone()

        self.opacity_timer = QTimer(self)
        self.opacity_timer.timeout.connect(self.fade_out)
        self.reset_opacity_timer()
        self.setWindowOpacity(1.0)

    def reset_opacity_timer(self):
        self.opacity_timer.start(10000)

    def fade_out(self):
        self.setWindowOpacity(0.3)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 122, 204, 220))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        self.setWindowOpacity(1.0)
        self.reset_opacity_timer()
        self.drag_start_pos = event.globalPos() - self.pos()

        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.exit_zone.show()
            screen_geometry = QApplication.primaryScreen().geometry()
            self.exit_zone.move(screen_geometry.width() - 100, screen_geometry.height() - 100)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.setWindowOpacity(1.0)
        self.reset_opacity_timer()
        self.exit_zone.hide()

        was_dragging = self.dragging
        self.dragging = False

        if was_dragging:
            if self.geometry().intersects(self.exit_zone.geometry()):
                QApplication.quit()
                return
        else:
            self.toggle_panel()

        self.drag_start_pos = None

    def toggle_panel(self):
        if self.panel and self.panel.isVisible():
            self.panel.close()
        else:
            shortcuts = []
            if os.path.exists(SHORTCUTS_FILE):
                with open(SHORTCUTS_FILE, 'r') as f:
                    try:
                        shortcuts = json.load(f)
                    except:
                        pass
            self.panel = ShortcutPanel(shortcuts, self)
            self.panel.move(self.x() + self.width(), self.y())
            self.panel.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ensure_default_icon()
    window = QuickBall()
    window.show()
    sys.exit(app.exec_())