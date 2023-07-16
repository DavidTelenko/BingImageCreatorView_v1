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
        self.originalImage = None
        self.upscaledImage = None

        saveIcon = QIcon("res/icons/save.svg")
        copyIcon = QIcon("res/icons/copy.svg")
        upscaleIcon = QIcon("res/icons/upscale.svg")
        originalIcon = QIcon("res/icons/original.svg")
        deleteIcon = QIcon("res/icons/delete.svg")
        backupIcon = QIcon("res/icons/backup.svg")
        editIcon = QIcon("res/icons/edit.svg")
        nextIcon = QIcon("res/icons/next.svg")
        prevIcon = QIcon("res/icons/prev.svg")

        self.saveAction = QAction(saveIcon, self.tr("Save"), self)
        self.saveAction.setShortcut("Ctrl+S")
        saveShortcut = QShortcut("Ctrl+S", self)
        saveShortcut.activated.connect(self.saveImage)
        self.saveAction.triggered.connect(self.saveImage)

        self.copyAction = QAction(copyIcon, self.tr("Copy"), self)
        self.copyAction.setShortcut("Ctrl+C")
        copyShortcut = QShortcut("Ctrl+C", self)
        copyShortcut.activated.connect(self.copyImage)
        self.copyAction.triggered.connect(self.copyImage)

        self.upscaleAction = QAction(upscaleIcon, self.tr("Upscale"), self)
        self.upscaleAction.triggered.connect(self.upscaleImage)

        self.showUpscaledAction = QAction(
            upscaleIcon, self.tr("Show Upscaled"), self
        )
        self.showUpscaledAction.triggered.connect(self.swapToUpscaled)

        self.showOriginalAction = QAction(
            originalIcon, self.tr("Show Original"), self
        )
        self.showOriginalAction.triggered.connect(self.swapToOriginal)

        self.deleteAction = QAction(deleteIcon, self.tr("Delete"), self)
        self.deleteAction.setShortcut("Shift+Del")
        deleteShortcut = QShortcut("Shift+Del", self)
        deleteShortcut.activated.connect(self.deleteImage)
        self.deleteAction.triggered.connect(self.deleteImage)

        self.backupAction = QAction(backupIcon, self.tr("Backup"), self)
        self.backupAction.triggered.connect(self.backupRequest.emit)

        self.copyPromptAction = QAction(copyIcon, self.tr("Copy Prompt"), self)
        self.copyPromptAction.setShortcut("Ctrl+Shift+C")
        copyPromptShortcut = QShortcut("Ctrl+Shift+C", self)
        copyPromptShortcut.activated.connect(self.copyPrompt)
        self.copyPromptAction.triggered.connect(self.copyPrompt)

        self.editPromptAction = QAction(editIcon, self.tr("Edit Prompt"), self)
        self.editPromptAction.triggered.connect(self.openPromptEditor)

        self.nextPictureAction = QAction(nextIcon, self.tr("Next"), self)
        nextShortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        nextShortcut.activated.connect(self.nextPicture.emit)
        self.nextPictureAction.setShortcut("Right")
        self.nextPictureAction.triggered.connect(self.nextPicture.emit)

        self.prevPictureAction = QAction(prevIcon, self.tr("Previous"), self)
        prevShortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        prevShortcut.activated.connect(self.prevPicture.emit)
        self.prevPictureAction.setShortcut("Left")
        self.prevPictureAction.triggered.connect(self.prevPicture.emit)

        self.setFullScreenAction = QAction(
            upscaleIcon, self.tr("Full Screen"), self
        )
        fullScreenShortcut = QShortcut(QKeySequence(Qt.Key_F), self)
        fullScreenShortcut.activated.connect(self.setFullScreen.emit)
        self.setFullScreenAction.setShortcut("F")
        self.setFullScreenAction.triggered.connect(self.setFullScreen.emit)

        self.promptEdit = PromptEditor(self)
        self.promptEdit.notifyPromptChange.connect(self.editPrompt)

        self.menu.addAction(self.saveAction)           # 0
        self.menu.addAction(self.copyAction)           # 1
        self.menu.addAction(self.upscaleAction)        # 2
        self.menu.addAction(self.deleteAction)         # 3
        self.menu.addAction(self.backupAction)         # 4
        self.menu.addSeparator()                       # _
        self.menu.addAction(self.editPromptAction)     # 5
        self.menu.addSeparator()                       # _
        self.menu.addAction(self.nextPictureAction)    # 6
        self.menu.addAction(self.prevPictureAction)    # 7
        self.menu.addAction(self.setFullScreenAction)  # 8

        self.setStyle(DummyStyle())

    promptChangeRequest = pyqtSignal(str)
    upscaleRequest = pyqtSignal()
    backupRequest = pyqtSignal()
    deleteRequest = pyqtSignal()
    saveRequest = pyqtSignal()
    nextPicture = pyqtSignal()
    prevPicture = pyqtSignal()
    setFullScreen = pyqtSignal()

    def openPromptEditor(self):
        self.promptEdit.exec_(self.prompt)

    def editPrompt(self, prompt):
        self.setPrompt(prompt)
        self.promptChangeRequest.emit(prompt)

    def setUpscaled(self, image):
        self.upscaledImage = image

        if self.upscaledImage:
            self.menu.removeAction(self.upscaleAction)
            self.menu.insertAction(self.deleteAction, self.showUpscaledAction)
        else:
            self.menu.removeAction(self.showUpscaledAction)
            self.menu.removeAction(self.showOriginalAction)
            self.menu.insertAction(self.deleteAction, self.upscaleAction)

    def setPrompt(self, prompt):
        self.prompt = prompt

        if self.prompt:
            self.menu.insertAction(
                self.editPromptAction,
                self.copyPromptAction
            )
        else:
            self.menu.removeAction(self.copyPromptAction)

    def setFilePath(self, path):
        self.filePath = path

    def setPixmap(self, pm: QPixmap) -> None:
        super().setPixmap(pm)
        self.updateMargins()
        self.originalImage = pm

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

    def swapToUpscaled(self):
        super().setPixmap(self.upscaledImage)
        self.updateMargins()

        self.menu.removeAction(self.showUpscaledAction)
        self.menu.insertAction(self.deleteAction, self.showOriginalAction)

    def swapToOriginal(self):
        super().setPixmap(self.originalImage)
        self.updateMargins()

        self.menu.removeAction(self.showOriginalAction)
        self.menu.insertAction(self.deleteAction, self.showUpscaledAction)
