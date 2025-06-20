import sys
import os
import json
import shutil
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLineEdit,
    QLabel, QDialog, QHBoxLayout, QMessageBox, QScrollArea
)
from PyQt5.QtGui import QPainter, QColor, QIcon, QPixmap, QCursor
from PyQt5.QtCore import Qt, QPoint, QTimer

SHORTCUTS_FILE = 'shortcuts.json'
ICONS_DIR = 'icons'
DEFAULT_ICON = os.path.join(ICONS_DIR, 'default.png')


def ensure_default_icon():
    if not os.path.exists(ICONS_DIR):
        os.makedirs(ICONS_DIR)
    if not os.path.exists(DEFAULT_ICON):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(180, 180, 180))
        pixmap.save(DEFAULT_ICON)


class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Shortcut")
        self.setFixedSize(300, 200)
        self.icon_path = DEFAULT_ICON

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter name")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter path or URL")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)

        icon_button = QPushButton("Choose Icon")
        icon_button.clicked.connect(self.choose_icon)

        add_button = QPushButton("Add")
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

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.scroll_content)

        self.main_layout.addWidget(self.scroll)

        self.draw_items()

        add_btn = QPushButton("+ Add Shortcut")
        add_btn.clicked.connect(self.add_shortcut)
        self.main_layout.addWidget(add_btn)

    def draw_items(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for i, s in enumerate(self.shortcuts):
            row = QWidget()
            row_layout = QHBoxLayout()
            row.setLayout(row_layout)

            icon = QIcon(s.get('icon', DEFAULT_ICON))
            btn = QPushButton(icon, s['name'])
            btn.clicked.connect(lambda _, path=s['path']: self.launch_item(path))

            drag_btn = QPushButton("↕")
            drag_btn.setToolTip("Drag to reorder")
            drag_btn.pressed.connect(lambda i=i: self.start_drag(i))

            del_btn = QPushButton("🗑")
            del_btn.clicked.connect(lambda _, i=i: self.delete_shortcut(i))

            row_layout.addWidget(btn)
            row_layout.addWidget(drag_btn)
            row_layout.addWidget(del_btn)

            self.scroll_layout.addWidget(row)

    def start_drag(self, index):
        self.dragging_index = index
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        widget = self.childAt(event.pos())
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i).widget()
            if item and widget in item.children():
                if i != self.dragging_index:
                    self.shortcuts[i], self.shortcuts[self.dragging_index] = self.shortcuts[self.dragging_index], self.shortcuts[i]
                    self.save()
                    self.dragging_index = i
                break

    def mouseReleaseEvent(self, event):
        self.setMouseTracking(False)

    def launch_item(self, path):
        try:
            if path.startswith("http"):
                webbrowser.open(path)
            else:
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self.close()

    def delete_shortcut(self, index):
        del self.shortcuts[index]
        self.save()

    def add_shortcut(self):
        dialog = ShortcutDialog(self)
        if dialog.exec_():
            name, path, icon = dialog.get_data()
            self.shortcuts.append({'name': name, 'path': path, 'icon': icon})
            self.save()

    def save(self):
        with open(SHORTCUTS_FILE, 'w') as f:
            json.dump(self.shortcuts, f, indent=2)
        self.draw_items()


class CloseZone(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(100, 100)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(50, QApplication.primaryScreen().geometry().height() - 150)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 0, 0, 180))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, self.width(), self.height())
        p.setPen(Qt.white)
        p.drawText(self.rect(), Qt.AlignCenter, "X")


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
        self.close_zone = CloseZone()

        self.last_mouse_pos = QCursor.pos()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_if_idle)
        self.timer.start(10000)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 122, 204, 220))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

    def fade_if_idle(self):
        if QCursor.pos() == self.last_mouse_pos:
            self.setWindowOpacity(0.3)
        else:
            self.setWindowOpacity(1.0)
        self.last_mouse_pos = QCursor.pos()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPos() - self.pos()
            self.close_zone.show()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_start_pos)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.close_zone.hide()
        if self.close_zone.geometry().contains(event.globalPos()):
            QApplication.quit()
        else:
            if (event.globalPos() - self.drag_start_pos - self.pos()).manhattanLength() < 10:
                self.toggle_panel()

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