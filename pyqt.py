import sys
import random
from PySide6 import QtWidgets, QtCore

class VideoStream(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Wii U Gamepad Stream")
        self.resize(854, 480)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)

        label = QtWidgets.QLabel("Hello", self)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(label)
    
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

        self.button.clicked.connect(self.start_stream)

    def start_stream(self):
        self.output_window = VideoStream(self)
        self.output_window.show()

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Wii U Gamepad Monitor")
        container = MainContainer()
        self.setCentralWidget(container)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Main()
    widget.resize(1000, 1000)
    widget.show()

    sys.exit(app.exec())