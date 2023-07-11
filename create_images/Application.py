from dataclasses import dataclass
import logging
import os
import pathlib
import time
from typing import List
import uuid
import BingImageCreator
from PyQt5 import QtGui
import dotenv
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import qdarktheme
from PIL import Image, ImageQt
import PIL.ExifTags
import torch
from create_images.Img import Img
from create_images.LoadingSpinner import LoadingSpinnerWidget
from create_images.Utils import apply_function_to_files
from create_images.ErrorDialog import ErrorDialog
import cv2
import qimage2ndarray
from RealESRGAN import RealESRGAN

config = dotenv.dotenv_values(".env")


@dataclass
class ImageData:
    image: QPixmap
    prompt: str
    file: str


class ImageGenerator(QObject):
    def __init__(
        self,
        outDir,
        historyFile,
        generator,
        watermarkMask,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.watermarkMask = watermarkMask
        self.historyFile = historyFile
        self.outDir = outDir
        self.generator = generator

    generated = pyqtSignal(object)
    started = pyqtSignal()
    finished = pyqtSignal()

    @pyqtSlot(str)
    def generateImages(self, prompt):
        self.started.emit()
        try:
            imagesLinks = self.generator.get_images(prompt)
            generatedImages = []

            if not os.path.exists(self.outDir) or not os.path.isdir(self.outDir):
                os.mkdir(self.outDir)

            with open(self.historyFile, "a") as history:
                for link in imagesLinks:
                    with self.generator.session.get(link, stream=True) as res:
                        # requesting image
                        res.raise_for_status()

                        # loading image from response
                        pixmap = QPixmap()
                        pixmap.loadFromData(res.content, "JPEG")

                        # removing watermark
                        pixmap = self.inpaintWatermark(pixmap)

                        # saving image file
                        outFilePath = self.getUniquePath()
                        pixmap.save(outFilePath.as_posix(), "JPEG")

                        # saving prompt to history
                        history.write(f"{prompt} :: [{outFilePath}]\n")

                        # including prompt to exif comment metadata tag
                        self.includeMetadata(outFilePath, prompt)

                        # adding image to generated images
                        generatedImages.append(
                            ImageData(pixmap, prompt, outFilePath.as_posix())
                        )
            self.generated.emit(generatedImages)
        except Exception as e:
            raise e
        finally:
            self.finished.emit()

    def getUniquePath(self):
        return self.outDir.absolute() / f"{uuid.uuid4()}.jpg"

    def includeMetadata(self, outFilePath, prompt):
        with Image.open(outFilePath) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(outFilePath, exif=metadata)

    def inpaintWatermark(self, pixmap: QPixmap) -> QPixmap:
        return QPixmap.fromImage(
            qimage2ndarray.array2qimage(
                cv2.inpaint(
                    qimage2ndarray.rgb_view(pixmap.toImage()),
                    self.watermarkMask,
                    3,
                    cv2.INPAINT_TELEA
                )
            )
        )


class ImageUpscaler(QObject):
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


class Application(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.outDir = pathlib.Path(config["OUTPUT_DIR"])
        self.upscaledDir = pathlib.Path(config["UPSCALED_DIR"])

        self.images = []
        self.currentImage = 0

        self.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        self.setWindowTitle("Bing Image Creator")
        self.setMinimumSize(800, 800)

        self.imageGenerator = ImageGenerator(
            outDir=self.outDir,
            historyFile=config["HISTORY_FILE"],
            generator=BingImageCreator.ImageGen(
                auth_cookie=config["TOKEN"],
                quiet=True,
            ),
            watermarkMask=cv2.imread(
                "res/bing-mask.png",
                cv2.IMREAD_GRAYSCALE
            )
        )
        self.imageGenerator.generated.connect(self.receiveGeneratedImages)

        self.imageGeneratorThread = QThread(self)
        self.imageGeneratorThread.setObjectName("imageGeneratorThread")
        self.imageGenerator.moveToThread(self.imageGeneratorThread)
        self.imageGeneratorThread.start()

        self.imageUpscaler = ImageUpscaler(
            outDir=self.upscaledDir,
            scale=int(config["UPSCALER_SCALE"]),
            model=config["UPSCALE_MODEL"]
        )
        self.imageUpscaler.upscaled.connect(self.onUpscaled)

        self.imageUpscalerThread = QThread(self)
        self.imageUpscalerThread.setObjectName("imageUpscalerThread")
        self.imageUpscaler.moveToThread(self.imageUpscalerThread)
        self.imageUpscalerThread.start()

        self.imageLabel = Img(self)
        self.imageLabel.setText("No images generated")
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.notifyPromptChange.connect(self.changeMetadata)
        self.imageLabel.imageDeleted.connect(self.deleteImage)
        self.imageLabel.upscaleRequest.connect(self.upscaleCurrentImage)

        search = QHBoxLayout()
        self.main = QVBoxLayout()

        self.prepend = QLineEdit(self)
        self.prompt = QLineEdit(self)
        self.append = QLineEdit(self)
        self.acceptButton = QPushButton(self)
        self.acceptButton.setText("Generate")

        self.prepend.setPlaceholderText("Prepend")
        self.prepend.setMaximumWidth(200)
        self.prompt.setPlaceholderText("Prompt")
        self.append.setPlaceholderText("Append")

        search.addWidget(self.prepend)
        search.addWidget(self.prompt)
        search.addWidget(self.acceptButton)

        self.main.addLayout(search)
        self.main.addStretch()
        self.main.addWidget(self.imageLabel)

        dummy = QWidget()
        dummy.setLayout(self.main)
        self.setCentralWidget(dummy)

        self.acceptButton.setFocusProxy(self)
        self.imageLabel.setFocusProxy(self)

        self.acceptButton.pressed.connect(self.generateImages)
        self.prompt.returnPressed.connect(self.generateImages)

        self.loadingSpinner = LoadingSpinnerWidget(
            self, True, True, Qt.Dialog | Qt.FramelessWindowHint
        )
        self.loadingSpinner.setAttribute(Qt.WA_TranslucentBackground)
        self.loadingSpinner.setWindowModality(Qt.ApplicationModal)
        self.loadingSpinner.setRoundingPercent(1.0)
        self.loadingSpinner.setMinimumTrailOpacity(0.3)
        self.loadingSpinner.setTrailFadePercentage(0.8)
        self.loadingSpinner.setNumberOfLines(12)
        self.loadingSpinner.setLineLength(8)
        self.loadingSpinner.setLineWidth(8)
        self.loadingSpinner.setInnerRadius(15)
        self.loadingSpinner.setRevolutionsPerSecond(1.5)
        self.loadingSpinner.setColor(Qt.white)

        self.imageGenerator.started.connect(self.loadingSpinner.start)
        self.imageGenerator.finished.connect(self.loadingSpinner.stop)

        self.imageUpscaler.started.connect(self.loadingSpinner.start)
        self.imageUpscaler.finished.connect(self.loadingSpinner.stop)

        self.loadState()

    @pyqtSlot()
    def generateImages(self):
        if not self.prompt.text():
            return

        prompt = self.prepend.text() + " " + self.prompt.text()

        try:
            QMetaObject.invokeMethod(
                self.imageGenerator,
                "generateImages",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, prompt),
            )
        except Exception as e:
            dialog = ErrorDialog(
                e, "Do not panic and try different prompt", self
            )
            dialog.exec_()

        self.setFocus()

    @pyqtSlot()
    def upscaleCurrentImage(self):
        try:
            QMetaObject.invokeMethod(
                self.imageUpscaler,
                "upscaleImage",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(QPixmap, self.images[self.currentImage].image),
            )
        except Exception as e:
            dialog = ErrorDialog(e, "Upscaling failed!", self)
            dialog.exec_()

    def closeEvent(self, _: QCloseEvent) -> None:
        self.saveState()

    def saveState(self):
        dotenv.set_key(".env", "PREPEND", self.prepend.text())
        dotenv.set_key(".env", "PROMPT", self.prompt.text())

    def loadState(self):
        self.prepend.setText(config["PREPEND"])
        self.prompt.setText(config["PROMPT"])

        def loadImage(i):
            try:
                self.images.append(
                    ImageData(QPixmap(i), self.getMetadata(i), i)
                )
            except Exception as e:
                logging.debug(f"Error while loading file \"{i}\":\n {e}")

        apply_function_to_files(loadImage, self.outDir.as_posix())
        self.images.sort(key=lambda x: -os.path.getctime(x.file))
        self.setImage(0)
        self.setFocus()

    @pyqtSlot()
    def deleteImage(self):
        self.images.pop(self.currentImage)
        self.setImage(self.currentImage)

    @pyqtSlot(str)
    def changeMetadata(self, prompt):
        if not prompt:
            return

        currentFile = self.images[self.currentImage].file

        with Image.open(currentFile) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(currentFile, exif=metadata)

    def getMetadata(self, imgPath):
        with Image.open(imgPath) as image:
            return image.getexif().get(PIL.ExifTags.Base.XPComment)

    @pyqtSlot(object)
    def receiveGeneratedImages(self, images):
        self.images = images + self.images
        self.setImage(0)

    def setImage(self, i):
        self.currentImage = i % len(self.images)
        self.imageLabel.setPixmap(self.images[self.currentImage].image)
        self.imageLabel.setPrompt(self.images[self.currentImage].prompt)
        self.imageLabel.setFilePath(self.images[self.currentImage].file)

    @pyqtSlot(object)
    def onUpscaled(self, image: Image):
        image.save(
            os.path.join(
                self.upscaledDir,
                os.path.basename(self.images[self.currentImage].file)
            )
        )
        self.setImage(self.currentImage)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super().mousePressEvent(e)
        self.setFocus()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        match e.key():
            case Qt.Key.Key_Right:
                self.setImage(self.currentImage + 1)
            case Qt.Key.Key_Left:
                self.setImage(self.currentImage - 1)
            case Qt.Key.Key_F:
                if self.isFullScreen():
                    self.showNormal()
                else:
                    self.showFullScreen()
