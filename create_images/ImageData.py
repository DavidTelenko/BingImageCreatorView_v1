
from dataclasses import dataclass
from PyQt5.QtGui import QPixmap


@dataclass
class ImageData:
    image: QPixmap
    prompt: str
    file: str
