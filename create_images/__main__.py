from create_images.Application import Application
from PyQt5.QtWidgets import QApplication
import sys


def main():
    qapp = QApplication(sys.argv)
    app = Application()
    app.show()

    sys.exit(qapp.exec_())


if __name__ == "__main__":
    main()
