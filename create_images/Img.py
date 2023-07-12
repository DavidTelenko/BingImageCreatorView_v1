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


class PromptEditor(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle(self.tr("Edit Prompt"))

        layout = QVBoxLayout()
        buttons = QHBoxLayout()

        minWidth = 300
        widthOffset = 20
        buttonMinWidth = 100
        height = 80

        self.promptEdit = QLineEdit(self)
        self.promptEdit.setPlaceholderText(self.tr("Prompt"))

        fm = QFontMetrics(self.promptEdit.font())

        def adjustSize():
            self.promptEdit.setMinimumWidth(
                max(fm.width(self.promptEdit.text()) + widthOffset, minWidth)
            )
            self.adjustSize()

        self.promptEdit.textChanged.connect(adjustSize)
        self.promptEdit.setMinimumWidth(minWidth)

        okButton = QPushButton(self.tr("Ok"), self)
        okButton.setMaximumWidth(buttonMinWidth)
        okButton.setFocusPolicy(Qt.NoFocus)
        okButton.pressed.connect(self.accept)

        cancelButton = QPushButton(self.tr("Cancel"), self)
        cancelButton.setMaximumWidth(buttonMinWidth)
        cancelButton.setFocusPolicy(Qt.NoFocus)
        cancelButton.pressed.connect(self.reject)

        def savePrompt():
            self.notifyPromptChange.emit(self.promptEdit.text())

        self.accepted.connect(savePrompt)
        self.promptEdit.returnPressed.connect(self.accept)

        buttons.addStretch()
        buttons.addWidget(okButton)
        buttons.addWidget(cancelButton)

        layout.addWidget(self.promptEdit)
        layout.addLayout(buttons)

        self.setLayout(layout)
        self.setFixedHeight(height)

    notifyPromptChange = pyqtSignal(str)

    def exec_(self, prompt):
        self.promptEdit.setText(prompt)
        return super().exec_()


class Img(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.menu = QMenu(self)
        self.prompt = ""
        self.filePath = None
        self.initialPixmap = None
        self._index = None

        saveIcon = QIcon("res/icons/save.svg")
        copyIcon = QIcon("res/icons/copy.svg")
        upscaleIcon = QIcon("res/icons/upscale.svg")
        deleteIcon = QIcon("res/icons/delete.svg")
        backupIcon = QIcon("res/icons/backup.svg")
        editIcon = QIcon("res/icons/edit.svg")

        self.saveAction = QAction(saveIcon, self.tr("Save"), self)
        self.saveAction.triggered.connect(self.saveImage)

        self.copyAction = QAction(copyIcon, self.tr("Copy"), self)
        self.copyAction.triggered.connect(self.copyImage)

        self.upscaleAction = QAction(upscaleIcon, self.tr("Upscale"), self)
        self.upscaleAction.triggered.connect(self.upscaleImage)

        self.deleteAction = QAction(deleteIcon, self.tr("Delete"), self)
        self.deleteAction.triggered.connect(self.deleteImage)

        self.backupAction = QAction(backupIcon, self.tr("Backup"), self)
        self.backupAction.triggered.connect(self.backupRequest.emit)

        self.copyPromptAction = QAction(copyIcon, self.tr("Copy Prompt"), self)
        self.copyPromptAction.triggered.connect(self.copyPrompt)

        self.editPromptAction = QAction(editIcon, self.tr("Edit Prompt"), self)
        self.editPromptAction.triggered.connect(self.openPromptEditor)

        self.promptEdit = PromptEditor(self)
        self.promptEdit.notifyPromptChange.connect(self.editPrompt)

        self.menu.addAction(self.saveAction)
        self.menu.addAction(self.copyAction)
        self.menu.addAction(self.upscaleAction)
        self.menu.addAction(self.deleteAction)
        self.menu.addAction(self.backupAction)
        self.menu.addSeparator()
        self.menu.addAction(self.editPromptAction)

        self.setStyle(DummyStyle())

    promptChangeRequest = pyqtSignal(str)
    upscaleRequest = pyqtSignal()
    backupRequest = pyqtSignal()
    deleteRequest = pyqtSignal()
    saveRequest = pyqtSignal()

    def openPromptEditor(self):
        self.promptEdit.exec_(self.prompt)

    def editPrompt(self, prompt):
        self.setPrompt(prompt)
        self.promptChangeRequest.emit(prompt)

    def setPrompt(self, prompt):
        self.prompt = prompt

        if self.prompt:
            self.menu.addAction(self.copyPromptAction)
        else:
            self.menu.removeAction(self.copyPromptAction)

    def setFilePath(self, path):
        self.filePath = path

    def setPixmap(self, pm: QPixmap) -> None:
        self.updateMargins()
        super().setPixmap(pm)

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

    def resizeEvent(self, e: QResizeEvent) -> None:
        self.updateMargins()
        super().resizeEvent(e)

    def contextMenuEvent(self, event):
        self.menu.exec_(self.mapToGlobal(event.pos()))

    def copyPrompt(self):
        if self.prompt:
            QApplication.clipboard().setText(self.prompt)

    def copyImage(self):
        if not self.pixmap().isNull():
            QApplication.clipboard().setPixmap(self.pixmap())

    def saveImage(self):
        self.saveRequest.emit()

    def deleteImage(self):
        self.deleteRequest.emit()

    def upscaleImage(self):
        self.upscaleRequest.emit()
