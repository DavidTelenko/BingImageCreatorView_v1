from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class ErrorDialog(QDialog):
    def __init__(self, exception, msg, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.exceptionMsg = str(exception)
        self.msg = msg
        self.detailsShown = False

        self.setWindowTitle("Oops. Error occurred")

        layout = QVBoxLayout()
        buttons = QHBoxLayout()

        self.label = QLabel(self)
        self.label.setText(self.msg)

        detailsButton = QPushButton("Details", self)
        detailsButton.setMaximumWidth(100)
        detailsButton.pressed.connect(self.toggleDetails)
        detailsButton.setCheckable(True)

        okButton = QPushButton("Ok", self)
        okButton.setMaximumWidth(100)
        okButton.pressed.connect(self.accept)

        copyButton = QPushButton("Copy", self)
        copyButton.setToolTip("Copy Error Message")
        copyButton.pressed.connect(self.copyErrorMessage)

        buttons.addWidget(copyButton)
        buttons.addStretch()
        buttons.addWidget(detailsButton)
        buttons.addWidget(okButton)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addLayout(buttons)

        self.setLayout(layout)

    def toggleDetails(self):
        self.detailsShown = not self.detailsShown
        if self.detailsShown:
            self.label.setText(self.exceptionMsg)
        else:
            self.label.setText(self.msg)

    def copyErrorMessage(self):
        QApplication.clipboard().setText(self.exceptionMsg)
        QMessageBox.information(
            self, "Copied!", "Error details copied to clipboard"
        )
