import logging
import os
import pathlib
import BingImageCreator
import dotenv
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import qdarktheme
from PIL import Image
import PIL.ExifTags
from create_images.ImageBackupWorker import ImageBackupWorker
from create_images.ImageGenerationWorker import ImageGenerationWorker
from create_images.ImageUpscaleWorker import ImageUpscaleWorker
from create_images.Img import Img
from create_images.LoadingSpinner import LoadingSpinnerWidget
from create_images.Utils import apply_function_to_files
from create_images.ErrorDialog import ErrorDialog
from create_images.ImageData import ImageData
import cv2


config = dotenv.dotenv_values(".env")


class Application(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.outDir = pathlib.Path(config["OUTPUT_DIR"])
        self.upscaledDir = pathlib.Path(config["UPSCALED_DIR"])

        self.images = []
        self.currentImage = 0

        self.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        self.setWindowTitle(self.tr("Bing Image Creator"))
        self.setMinimumSize(800, 800)

        self.imageGenerationWorker = ImageGenerationWorker(
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
        self.imageGenerationWorker.generated.connect(
            self.receiveGeneratedImages
        )

        self.imageGenerationThread = QThread(self)
        self.imageGenerationThread.setObjectName("imageGenerationThread")
        self.imageGenerationWorker.moveToThread(self.imageGenerationThread)
        self.imageGenerationThread.start()

        self.imageUpscaleWorker = ImageUpscaleWorker(
            outDir=self.upscaledDir,
            scale=int(config["UPSCALER_SCALE"]),
            model=config["UPSCALE_MODEL"]
        )
        self.imageUpscaleWorker.upscaled.connect(self.onUpscaled)

        self.imageUpscaleThread = QThread(self)
        self.imageUpscaleThread.setObjectName("imageUpscaleThread")
        self.imageUpscaleWorker.moveToThread(self.imageUpscaleThread)
        self.imageUpscaleThread.start()

        self.imageBackupWorker = ImageBackupWorker()
        self.imageBackupThread = QThread(self)
        self.imageBackupThread.setObjectName("imageBackupThread")
        self.imageBackupWorker.moveToThread(self.imageBackupThread)
        self.imageBackupThread.start()

        self.imageLabel = Img(self)
        self.imageLabel.setText(self.tr("No images generated"))
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.promptChangeRequest.connect(
            self.changeCurrentImageMetadata
        )
        self.imageLabel.deleteRequest.connect(self.deleteCurrentImage)
        self.imageLabel.saveRequest.connect(self.saveCurrentImage)
        self.imageLabel.upscaleRequest.connect(self.upscaleCurrentImage)
        self.imageLabel.backupRequest.connect(self.backupCurrentImage)

        search = QHBoxLayout()
        self.main = QVBoxLayout()

        self.prepend = QLineEdit(self)
        self.prompt = QLineEdit(self)
        self.append = QLineEdit(self)
        self.acceptButton = QPushButton(self)
        self.acceptButton.setText(self.tr("Generate"))

        self.prepend.setPlaceholderText(self.tr("Prepend"))
        self.prepend.setMaximumWidth(200)
        self.prompt.setPlaceholderText(self.tr("Prompt"))
        self.append.setPlaceholderText(self.tr("Append"))

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

        self.imageGenerationWorker.started.connect(self.loadingSpinner.start)
        self.imageGenerationWorker.finished.connect(self.loadingSpinner.stop)

        self.imageUpscaleWorker.started.connect(self.loadingSpinner.start)
        self.imageUpscaleWorker.finished.connect(self.loadingSpinner.stop)

        self.loadState()

    @pyqtSlot()
    def generateImages(self):
        if not self.prompt.text():
            return

        prompt = self.prepend.text() + " " + self.prompt.text()

        try:
            QMetaObject.invokeMethod(
                self.imageGenerationWorker,
                "generateImages",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, prompt),
            )
        except Exception as e:
            dialog = ErrorDialog(
                e, self.tr("Do not panic and try different prompt"), self
            )
            dialog.exec_()

    @pyqtSlot()
    def upscaleCurrentImage(self):
        try:
            QMetaObject.invokeMethod(
                self.imageUpscaleWorker,
                "upscaleImage",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(QPixmap, self.images[self.currentImage].image),
            )
        except Exception as e:
            dialog = ErrorDialog(
                e, self.tr("Upscaling failed!"), self
            )
            dialog.exec_()

    @pyqtSlot()
    def backupCurrentImage(self):
        try:
            QMetaObject.invokeMethod(
                self.imageBackupWorker,
                "backupImage",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(QPixmap, self.images[self.currentImage].image),
            )
        except Exception as e:
            dialog = ErrorDialog(
                e, self.tr("Backup failed!"), self
            )
            dialog.exec_()

    @pyqtSlot()
    def deleteCurrentImage(self):
        os.remove(self.images[self.currentImage].file)
        self.images.pop(self.currentImage)
        self.setImage(self.currentImage)

    @pyqtSlot()
    def saveCurrentImage(self):
        filePath, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Image"),
            "",
            "Image Files (*.png, *.jpg, *.jpeg, *jfif)"
        )
        if not filePath:
            return
        self.images[self.currentImage].image.save(filePath)

    @pyqtSlot(str)
    def changeCurrentImageMetadata(self, prompt):
        if not prompt:
            return

        currentFile = self.images[self.currentImage].file

        with Image.open(currentFile) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(currentFile, exif=metadata)

    def closeEvent(self, e: QCloseEvent):
        self.saveState()
        super().closeEvent(e)

    def saveState(self):
        dotenv.set_key(".env", "PREPEND", self.prepend.text())
        dotenv.set_key(".env", "PROMPT", self.prompt.text())

    def loadState(self):
        self.prepend.setText(config["PREPEND"])
        self.prompt.setText(config["PROMPT"])

        def loadImage(filepath):
            try:
                with Image.open(filepath) as image:
                    self.images.append(
                        ImageData(
                            QPixmap(filepath),
                            image.getexif().get(PIL.ExifTags.Base.XPComment),
                            filepath
                        )
                    )
            except Exception as e:
                logging.debug(
                    f"Error while loading file \"{filepath}\":\n {e}"
                )

        apply_function_to_files(loadImage, self.outDir.as_posix())
        self.images.sort(key=lambda x: -os.path.getctime(x.file))
        self.setImage(0)
        self.setFocus()

    @pyqtSlot(object)
    def receiveGeneratedImages(self, images):
        self.images = images + self.images
        self.setImage(0)
        self.setFocus()

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
        self.setFocus()
        super().mousePressEvent(e)

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
