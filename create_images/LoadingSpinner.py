import math
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtMultimedia import *
import numpy as np


class LoadingSpinnerWidget(QWidget):
    def __init__(self, centerOnParent=True, disableParentWhenSpinning=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._centerOnParent = centerOnParent
        self._disableParentWhenSpinning = disableParentWhenSpinning
        self._color = Qt.black
        self._roundingPercent = 1.0
        self._minimumTrailOpacity = 0.1
        self._trailFadePercentage = 0.8
        self._revolutionsPerSecond = 1.57079632679489661923
        self._numberOfLines = 20
        self._lineLength = 10
        self._lineWidth = 2
        self._innerRadius = 10
        self._currentCounter = 0
        self._isSpinning = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.rotate)

        self.stopped.connect(self.stop)
        self.started.connect(self.start)

        self.updateSize()
        self.updateTimer()
        self.hide()

    def paintEvent(self, event):
        # self.updatePosition()
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self._currentCounter >= self._numberOfLines:
            self._currentCounter = 0

        painter.setPen(Qt.NoPen)

        for i in range(self._numberOfLines):
            painter.save()
            painter.translate(
                self._innerRadius + self._lineLength,
                self._innerRadius + self._lineLength
            )
            rotateAngle = 360 * i / self._numberOfLines
            painter.rotate(rotateAngle)
            painter.translate(self._innerRadius, 0)

            painter.setBrush(
                self.currentLineColor(
                    self.lineCountDistanceFromPrimary(i)
                )
            )

            halfWidth = self._lineWidth / 2
            roundness = halfWidth * self._roundingPercent

            painter.drawRoundedRect(
                QRectF(0, -halfWidth, self._lineLength, self._lineWidth),
                roundness, roundness
            )
            painter.restore()

    stopped = pyqtSignal()
    started = pyqtSignal()

    def start(self):
        self.updatePosition()
        self._isSpinning = True
        self.show()

        if self.parentWidget() and self._disableParentWhenSpinning:
            self.parentWidget().setEnabled(False)

        if not self._timer.isActive():
            self._timer.start()
            self._currentCounter = 0

    def stop(self):
        self._isSpinning = False
        self.hide()

        if self.parentWidget() and self._disableParentWhenSpinning:
            self.parentWidget().setEnabled(True)

        if self._timer.isActive():
            self._timer.stop()
            self._currentCounter = 0

    def rotate(self):
        self._currentCounter += 1
        if self._currentCounter >= self._numberOfLines:
            self._currentCounter = 0
        self.update()

    def updateSize(self):
        size = (self._innerRadius + self._lineLength) * 2
        self.setFixedSize(size, size)

    def updateTimer(self):
        self._timer.setInterval(
            round(1000 / (self._numberOfLines * self._revolutionsPerSecond))
        )

    def updatePosition(self):
        if self.parentWidget() and self._centerOnParent:
            cX = self.parentWidget().geometry().center().x()
            cY = self.parentWidget().geometry().center().y()
            w = self.size().width()
            h = self.size().height()
            self.move(cX - w // 2, cY - h // 2)

    def lineCountDistanceFromPrimary(self, current):
        distance = self._currentCounter - current
        if (distance < 0):
            distance += self._numberOfLines
        return distance

    def currentLineColor(self, countDistance):
        color = QColor(self._color)
        if (countDistance == 0):
            return color

        minAlphaF = self._minimumTrailOpacity
        distanceThreshold = math.ceil(
            (self._numberOfLines - 1) * self._trailFadePercentage
        )

        if (countDistance > distanceThreshold):
            color.setAlphaF(minAlphaF)
            return color

        alphaDiff = color.alphaF() - minAlphaF
        gradient = alphaDiff / (distanceThreshold + 1)
        resultAlpha = color.alphaF() - gradient * countDistance

        # If alpha is out of bounds, clip it.
        color.setAlphaF(np.clip(resultAlpha, 0.0, 1.0))
        return color

    def setNumberOfLines(self, lines):
        self._numberOfLines = lines
        self._currentCounter = 0
        self.updateTimer()

    def setLineLength(self, length):
        self._lineLength = length
        self.updateSize()

    def setLineWidth(self, width):
        self._lineWidth = width

    def setInnerRadius(self, radius):
        self._innerRadius = radius
        self.updateSize()

    def color(self):
        return self._color

    def roundingPercent(self):
        return self._roundingPercent

    def minimumTrailOpacity(self):
        return self._minimumTrailOpacity * 100.0

    def trailFadePercentage(self):
        return self._trailFadePercentage

    def revolutionsPerSecond(self):
        return self._revolutionsPerSecond

    def numberOfLines(self):
        return self._numberOfLines

    def lineLength(self):
        return self._lineLength

    def lineWidth(self):
        return self._lineWidth

    def innerRadius(self):
        return self._innerRadius

    def isSpinning(self):
        return self._isSpinning

    def setRoundingPercent(self, roundness):
        self._roundingPercent = np.clip(roundness, 0.0, 1.0)

    def setColor(self, color):
        self._color = color

    def setRevolutionsPerSecond(self, revolutionsPerSecond):
        self._revolutionsPerSecond = revolutionsPerSecond
        self.updateTimer()

    def setTrailFadePercentage(self, trail):
        self._trailFadePercentage = trail

    def setMinimumTrailOpacity(self, minimumTrailOpacity):
        self._minimumTrailOpacity = minimumTrailOpacity


class LoadingManager:
    def __init__(self, loadingSpinner: LoadingSpinnerWidget):
        self.loadingSpinner = loadingSpinner

    def __enter__(self):
        self.loadingSpinner.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.loadingSpinner.stop()
