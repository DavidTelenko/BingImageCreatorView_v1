import sys
from PyQt5 import QtGui
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class Img(QMainWindow):
    def __init__(self, imgPath, parent=None):
        super().__init__(parent)
        self.qimg = QPixmap(imgPath)

    def paintEvent(self, e):
        painter = QPainter(self)
        windowRect = e.rect()
        pixmap = self.qimg.scaled(
            windowRect.width(), windowRect.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        rect = pixmap.rect()
        rect.moveCenter(windowRect.center())
        painter.drawPixmap(rect, pixmap)
