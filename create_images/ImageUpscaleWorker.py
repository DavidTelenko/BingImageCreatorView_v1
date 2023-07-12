import logging
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PIL import ImageQt
import torch
from RealESRGAN import RealESRGAN


class ImageUpscaleWorker(QObject):
    def __init__(
        self,
        outDir,
        scale,
        model,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.outDir = outDir
        self.deviseType = 'cuda' if torch.cuda.is_available() else 'cpu'

        logging.info(f"Selected device type: {self.deviseType}")

        self.model = RealESRGAN(
            device=torch.device(self.deviseType),
            scale=scale
        )
        self.model.load_weights(
            model_path=model,
            download=True
        )

    upscaled = pyqtSignal(object)
    started = pyqtSignal()
    finished = pyqtSignal()

    @pyqtSlot(QPixmap)
    def upscaleImage(self, image: QPixmap):
        self.started.emit()
        try:
            lrImage = ImageQt.fromqpixmap(image).convert("RGB")
            res = self.model.predict(lrImage)
            self.upscaled.emit(res)
        except Exception as e:
            raise e
        finally:
            self.finished.emit()
