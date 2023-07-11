from PyQt5 import QtGui
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import os


class DummyStyle(QProxyStyle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generatedIconPixmap(self, iconMode, pixmap, opt) -> QPixmap:
        return pixmap


class Img(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.menu = QMenu(self)
        self.prompt = ""
        self.filePath = None
        self.initialPixmap = None

        self.saveAction = QAction("Save", self)
        self.saveAction.triggered.connect(self.saveImage)

        self.copyAction = QAction("Copy", self)
        self.copyAction.triggered.connect(self.copyImage)

        self.deleteAction = QAction("Delete", self)
        self.deleteAction.triggered.connect(self.deleteImage)

        self.upscaleAction = QAction("Upscale", self)
        self.upscaleAction.triggered.connect(self.upscaleImage)

        self.copyPromptAction = QAction("Copy Prompt", self)
        self.copyPromptAction.triggered.connect(self.copyPrompt)

        self.editPromptAction = QAction("Edit Prompt", self)
        self.editPromptAction.triggered.connect(self.editPrompt)

        self.menu.addAction(self.saveAction)
        self.menu.addAction(self.copyAction)
        self.menu.addAction(self.upscaleAction)
        self.menu.addAction(self.deleteAction)
        self.menu.addAction(self.editPromptAction)

        self.setStyle(DummyStyle())

    notifyPromptChange = pyqtSignal(str)
    upscaleRequest = pyqtSignal()
    imageDeleted = pyqtSignal()

    def changeEvent(self, e: QEvent) -> None:
        if e.type() == QEvent.EnabledChange:
            if not self.isEnabled():
                blurEffect = QGraphicsBlurEffect(self)
                blurEffect.setBlurRadius(10)
                blurEffect.setBlurHints(QGraphicsBlurEffect.QualityHint)
                self.setGraphicsEffect(blurEffect)
            else:
                self.setGraphicsEffect(None)
        return super().changeEvent(e)

    def setPrompt(self, prompt):
        self.prompt = prompt
        if self.prompt:
            self.menu.addAction(self.copyPromptAction)
        else:
            self.menu.removeAction(self.copyPromptAction)

    def setFilePath(self, path):
        self.filePath = path

    def copyPrompt(self):
        clipboard = QApplication.clipboard()
        if self.prompt:
            clipboard.setText(self.prompt)

    def editPrompt(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Prompt")

        layout = QVBoxLayout()
        buttons = QHBoxLayout()

        promptEdit = QLineEdit(self)
        promptEdit.setPlaceholderText("Prompt")

        def adjustSize():
            text = promptEdit.text()
            font = promptEdit.font()
            fm = QFontMetrics(font)
            width = fm.width(text)
            promptEdit.setMinimumWidth(max(width + 20, 300))
            dialog.adjustSize()

        promptEdit.textChanged.connect(adjustSize)
        promptEdit.setText(self.prompt)
        promptEdit.setMinimumWidth(300)

        okButton = QPushButton("Ok", dialog)
        okButton.setMaximumWidth(100)
        okButton.setFocusPolicy(Qt.NoFocus)
        okButton.pressed.connect(dialog.accept)

        cancelButton = QPushButton("Cancel", dialog)
        cancelButton.setMaximumWidth(100)
        cancelButton.setFocusPolicy(Qt.NoFocus)
        cancelButton.pressed.connect(dialog.reject)

        def savePrompt():
            self.setPrompt(promptEdit.text())
            self.notifyPromptChange.emit(self.prompt)

        dialog.accepted.connect(savePrompt)

        buttons.addStretch()
        buttons.addWidget(okButton)
        buttons.addWidget(cancelButton)

        layout.addWidget(promptEdit)
        layout.addLayout(buttons)

        dialog.setLayout(layout)
        dialog.setFixedHeight(80)
        dialog.exec_()

    def setPixmap(self, pm: QPixmap) -> None:
        self.updateMargins()
        super().setPixmap(pm)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.updateMargins()
        super().resizeEvent(a0)

    def updateMargins(self):
        if self.pixmap() is None:
            return

        pw, ph = self.pixmap().width(), self.pixmap().height()
        w, h = self.width(), self.height()

        if pw <= 0 or ph <= 0 or w <= 0 or h <= 0:
            return

        if w * ph > h * pw:
            m = int((w - (pw * h / ph)) / 2)
            self.setContentsMargins(m, 0, m, 0)
        else:
            m = int((h - (ph * w / pw)) / 2)
            self.setContentsMargins(0, m, 0, m)

    def contextMenuEvent(self, event):
        self.menu.exec_(self.mapToGlobal(event.pos()))

    def saveImage(self):
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "Image Files (*.png, *.jpg, *.jpeg, *jfif)"
        )
        if filePath:
            self.pixmap().save(filePath)

    def deleteImage(self):
        if self.filePath:
            os.remove(self.filePath)
            self.imageDeleted.emit()

    def upscaleImage(self):
        self.upscaleRequest.emit()

    def copyImage(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap())
