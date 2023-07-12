import os
import uuid
from PyQt5.QtMultimedia import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PIL import Image
import PIL.ExifTags
import cv2
import qimage2ndarray


class ImageGenerationWorker(QObject):
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
