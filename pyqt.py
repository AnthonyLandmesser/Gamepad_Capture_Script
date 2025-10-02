import sys
import random

from PySide6 import QtWidgets, QtCore

import stream

class VideoStream(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wii U Gamepad Stream")
        self.resize(854, 480)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        label = QtWidgets.QLabel("No video source available.", self)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(label)

        stream.stream(video_stream=self)
        self.show()
    
    def set_image(self, image):
        for parsed_frame in parsed_frames:
            decoded_frames = CODEC.decode(parsed_frame)
            for decoded_frame in decoded_frames:
                image = decoded_frame.to_ndarray(format='bgr24')
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
        self.output_window = VideoStream()

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Wii U Gamepad Monitor")
        self.container = MainContainer()
        self.setCentralWidget(self.container)

    def closeEvent(self, event):
        if self.container.output_window:
            self.container.output_window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Main()
    widget.resize(1000, 1000)
    widget.show()

    sys.exit(app.exec())