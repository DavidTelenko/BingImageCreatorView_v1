from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class Img(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.menu = QMenu(self)
        self.prompt = ""

        self.saveAction = QAction("Save", self)
        self.saveAction.triggered.connect(self.saveImage)

        self.copyAction = QAction("Copy", self)
        self.copyAction.triggered.connect(self.copyImage)

        self.copyPromptAction = QAction("Copy Prompt", self)
        self.copyPromptAction.triggered.connect(self.copyPrompt)

        self.editPromptAction = QAction("Edit Prompt", self)
        self.editPromptAction.triggered.connect(self.editPrompt)

        self.menu.addAction(self.saveAction)
        self.menu.addAction(self.copyAction)
        self.menu.addAction(self.editPromptAction)

    def setPrompt(self, prompt):
        self.prompt = prompt
        if self.prompt:
            self.menu.addAction(self.copyPromptAction)
        else:
            self.menu.removeAction(self.copyPromptAction)

    notifyPromptChange = pyqtSignal(str)

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
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "Image Files (*.png, *.jpg, *.jpeg, *jfif)"
        )
        if filePath:
            self.pixmap().save(filePath)

    def copyImage(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap())
