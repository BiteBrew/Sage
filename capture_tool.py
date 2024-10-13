# capture_tool.py

from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QScreen, QPixmap
from PyQt5.QtCore import Qt, QRect, QPoint
import os
from constants import CAPTURE_FILE

class CaptureWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Screen Capture')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color:black;")
        self.setWindowOpacity(0.3)
        self.origin = QPoint()
        self.end = QPoint()
        self.rect = None

        # Get all screens
        self.screens = QApplication.screens()
        self.full_geometry = self.get_full_geometry()
        self.setGeometry(self.full_geometry)

        # Create a pixmap of the entire virtual desktop
        self.fullscreen = self.grab_full_screen()

    def get_full_geometry(self):
        # Calculate the bounding rectangle of all screens
        desktop = QDesktopWidget()
        total_rect = QRect()
        for i in range(desktop.screenCount()):
            total_rect = total_rect.united(desktop.screenGeometry(i))
        return total_rect

    def grab_full_screen(self):
        # Capture the entire virtual desktop
        full_pixmap = QPixmap(self.full_geometry.size())
        painter = QPainter(full_pixmap)
        for screen in self.screens:
            screen_geo = screen.geometry()
            screen_pixmap = screen.grabWindow(0)
            painter.drawPixmap(screen_geo.topLeft(), screen_pixmap)
        painter.end()
        return full_pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.rect:
            painter.setPen(QPen(QColor('red'), 2))
            painter.drawRect(self.rect)

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rect = None
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.rect = QRect(self.origin, self.end)
        self.update()

    def mouseReleaseEvent(self, event):
        QApplication.restoreOverrideCursor()
        self.hide()  # Hide the widget before capturing
        x1 = min(self.origin.x(), self.end.x())
        y1 = min(self.origin.y(), self.end.y())
        x2 = max(self.origin.x(), self.end.x())
        y2 = max(self.origin.y(), self.end.y())
        
        # Capture the screen area without the overlay
        img = self.fullscreen.copy(x1, y1, x2-x1, y2-y1)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(CAPTURE_FILE), exist_ok=True)
        
        img.save(CAPTURE_FILE)
        print(f"Image captured and saved as '{CAPTURE_FILE}'.")
        self.close()

def start_capture():
    app = QApplication.instance() or QApplication([])
    widget = CaptureWidget()
    widget.showFullScreen()
    app.exec_()
    return CAPTURE_FILE  # Return the path of the captured image

if __name__ == "__main__":
    start_capture()
