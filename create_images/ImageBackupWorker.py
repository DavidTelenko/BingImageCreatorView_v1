from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import time


class ImageBackupWorker(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    backupSaved = pyqtSignal(object)
    started = pyqtSignal()
    finished = pyqtSignal()

    @pyqtSlot(QPixmap)
    def backupImage(self, image: QPixmap):
        time.sleep(5)
        print(f"Backup of {image} finished")
