import sys
import random
from PySide6 import QtWidgets

class VideoStream(QtWidgets.QWidget):
    def __init__(self, message):
        super().__init__()
        self.resize(400, 300)

        label = QtWidgets.QLabel(message, self)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
    
    def set_image(self, image):
        qimage = QtWidgets.QImage(image, 854, 480, QImage.Format.Format_BGR888)
        self.label.setPixmap(QPixmap.fromImage(qimage))

class MainContainer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.button = QtWidgets.QPushButton("Click me!")
        self.label = QtWidgets.QLabel(self)
        self.label.setScaledContents(True)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)

        self.button.clicked.connect(self.request_iframe)

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.button = QtWidgets.QPushButton("Click me!")
        self.label = QtWidgets.QLabel(self)
        self.label.setScaledContents(True)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)

        self.button.clicked.connect(self.request_iframe)

    def request_iframe(self):
        self.output_window = OutputWindow("Hello World")
        self.output_window.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(1000, 1000)
    widget.show()

    sys.exit(app.exec())