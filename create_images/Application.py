from dataclasses import dataclass
import logging
import os
import pathlib
import uuid
import BingImageCreator
import dotenv
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import qdarktheme
from PIL import Image
import PIL.ExifTags
from create_images.Img import Img
from create_images.LoadingSpinner import LoadingSpinnerWidget
from create_images.Utils import apply_function_to_files
from create_images.ErrorDialog import ErrorDialog
import cv2
import qimage2ndarray


config = dotenv.dotenv_values(".env")


@dataclass
class ImageData:
    image: QPixmap
    prompt: str
    file: str


class MyThread(QThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        self.onRun.emit()

    onRun = pyqtSignal()  # Signal to emit when the task is complete


class Application(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.outDir = pathlib.Path(config["OUTPUT_DIR"])
        self.generator = BingImageCreator.ImageGen(
            auth_cookie=config["TOKEN"],
            quiet=True,
        )

        self.images = []
        self.currentImage = 0
        self.historyFile = config["HISTORY_FILE"]
        self.watermarkMask = cv2.imread(
            "res/bing-mask.png",
            cv2.IMREAD_GRAYSCALE
        )

        self.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        self.setWindowTitle("Bing Image Creator")
        self.setMinimumSize(800, 800)

        self.loadingSpinner = LoadingSpinnerWidget(self)
        self.loadingSpinner.setRoundingPercent(1.0)
        self.loadingSpinner.setMinimumTrailOpacity(0.3)
        self.loadingSpinner.setTrailFadePercentage(0.8)
        self.loadingSpinner.setNumberOfLines(12)
        self.loadingSpinner.setLineLength(8)
        self.loadingSpinner.setLineWidth(8)
        self.loadingSpinner.setInnerRadius(15)
        self.loadingSpinner.setRevolutionsPerSecond(1.5)
        self.loadingSpinner.setColor(Qt.white)

        self.worker = MyThread(self)
        self.worker.started.connect(self.loadingSpinner.start)
        self.worker.finished.connect(self.loadingSpinner.stop)
        self.worker.onRun.connect(self.runPrompt)

        self.imageLabel = Img(self)
        self.imageLabel.setText("No images generated")
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.notifyPromptChange.connect(self.changeMetadata)

        search = QHBoxLayout()
        main = QVBoxLayout()

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

        main.addLayout(search)
        main.addStretch()
        main.addWidget(self.loadingSpinner)
        main.addWidget(self.imageLabel)

        dummy = QWidget()
        dummy.setLayout(main)
        self.setCentralWidget(dummy)

        self.acceptButton.setFocusProxy(self)
        self.imageLabel.setFocusProxy(self)

        self.acceptButton.pressed.connect(self.worker.start)
        self.prompt.returnPressed.connect(self.worker.start)

        self.loadState()

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
        self.setImage(0)
        self.setFocus()

    def runPrompt(self):
        if not self.prompt.text():
            return

        prompt = self.prepend.text() + " " + self.prompt.text()
        self.imageLabel.clear()
        self.imageLabel.setText("Generating...")

        if not os.path.exists(self.outDir) or not os.path.isdir(self.outDir):
            os.mkdir(self.outDir)
        try:
            images = self.generator.get_images(prompt)

            with open(self.historyFile, "a") as history:
                for link in images:
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

                        # adding image to all current images
                        self.images.append(
                            ImageData(pixmap, prompt, outFilePath.as_posix())
                        )
            self.setImage(len(images) - 1)
            self.setFocus()
        except Exception as e:
            self.openErrorDialog(e)

    def openErrorDialog(self, e):
        dialog = ErrorDialog(e, "Do not panic and try different prompt", self)
        dialog.exec_()

    def getUniquePath(self):
        return self.outDir.absolute() / f"{uuid.uuid4()}.jpg"

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

    def changeMetadata(self, prompt):
        if not prompt:
            return

        currentFile = self.images[self.currentImage].file

        with Image.open(currentFile) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(currentFile, exif=metadata)

    def includeMetadata(self, outFilePath, prompt):
        with Image.open(outFilePath) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(outFilePath, exif=metadata)

    def getMetadata(self, imgPath):
        with Image.open(imgPath) as image:
            return image.getexif().get(PIL.ExifTags.Base.XPComment)

    def setImage(self, i):
        self.currentImage = i % len(self.images)
        self.imageLabel.setPixmap(self.images[self.currentImage].image)
        self.imageLabel.setPrompt(self.images[self.currentImage].prompt)

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
