from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class Img(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.menu = QMenu(self)

        saveAction = QAction("Save Image", self)
        saveAction.triggered.connect(self.saveImage)

        copyAction = QAction("Copy Image", self)
        copyAction.triggered.connect(self.copyImage)

        self.menu.addAction(saveAction)
        self.menu.addAction(copyAction)

    def paintEvent(self, e):
        if not self.pixmap():
            super().paintEvent(e)
            return

        painter = QPainter(self)
        windowRect = e.rect()

        pixmap = self.pixmap().scaled(
            windowRect.width(), windowRect.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        rect = pixmap.rect()
        rect.moveCenter(windowRect.center())
        painter.drawPixmap(rect, pixmap)

    def contextMenuEvent(self, event):
        self.menu.exec_(self.mapToGlobal(event.pos()))

    def saveImage(self):
        # Get file path and name from user
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "Image Files (*.png, *.jpg, *.jpeg, *jfif)"
        )
        if filePath:
            self.pixmap().save(filePath)

    def copyImage(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap())
