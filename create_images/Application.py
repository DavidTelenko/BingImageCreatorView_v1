import contextlib
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
import numpy as np
from PIL import Image
import PIL.ExifTags
from create_images.Img import Img
from create_images.LoadingSpinner import LoadingSpinnerWidget
import cv2
import qimage2ndarray

config = dotenv.dotenv_values(".env")


class Application(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.outDir = pathlib.Path(config["OUTPUT_DIR"])
        self.generator = BingImageCreator.ImageGen(
            config["TOKEN"],
            quiet=bool(config["QUIET"]),
        )

        self.images = []
        self.currentImage = 0
        self.historyFile = config["HISTORY_FILE"]
        self.watermarkMask = cv2.imread(
            "res/bing-mask.png", cv2.IMREAD_GRAYSCALE
        )

        self.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        self.setWindowTitle("Bing Image Creator")
        self.setMinimumSize(500, 500)

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

        self.worker = QThread()
        self.worker.started.connect(self.loadingSpinner.start)
        self.worker.finished.connect(self.loadingSpinner.stop)
        self.worker.run = self.runPrompt

        self.imageLabel = Img(self)
        self.imageLabel.setText("No images generated")
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)

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

        # self.images.append(
        #     QPixmap("output/2c6178e3-3881-4d53-867f-dce32cc21404.jpg")
        # )
        # self.setImage(0)

    def closeEvent(self, _: QCloseEvent) -> None:
        self.saveState()

    def saveState(self):
        dotenv.set_key(".env", "PREPEND", self.prepend.text())
        dotenv.set_key(".env", "PROMPT", self.prompt.text())

    def loadState(self):
        self.prepend.setText(config["PREPEND"])
        self.prompt.setText(config["PROMPT"])

    def runPrompt(self):
        if not self.prompt.text():
            return
        self.resetImages()
        prompt = self.prepend.text() + " " + self.prompt.text()
        images = self.generator.get_images(prompt)

        with contextlib.suppress(FileExistsError):
            os.mkdir(self.outDir)
        # try:
        with open(self.historyFile, "a") as history:
            for link in images:
                with self.generator.session.get(link, stream=True) as res:
                    res.raise_for_status()

                    pixmap = QPixmap()
                    pixmap.loadFromData(res.content, "JPEG")

                    pixmap = self.inpaintWatermark(pixmap)

                    outFilePath = self.getUniquePath()
                    pixmap.save(outFilePath.as_posix(), "JPEG")
                    history.write(f"{prompt} :: [{outFilePath}]\n")

                    # self.includeMetadata(outFilePath, prompt)

                    self.images.append(pixmap)
        self.setImage(0)
        self.setFocus()
        # except Exception as _:
        #     QMessageBox.critical(
        #         self,
        #         "Something went wrong",
        #         "Do not panic and try different promt)"
        #     )
        #     self.resetImages()

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

    def includeMetadata(self, outFilePath, prompt):
        with Image.open(outFilePath) as image:
            metadata = image.getexif()
            metadata[PIL.ExifTags.Base.XPComment] = prompt
            image.save(outFilePath, exif=metadata)

    def resetImages(self):
        self.images.clear()
        self.currentImage = 0
        self.imageLabel.clear()
        self.imageLabel.setText("No images generated")

    def setImage(self, i):
        self.currentImage = np.clip(i, 0, len(self.images) - 1)
        self.imageLabel.setPixmap(self.images[self.currentImage])

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
