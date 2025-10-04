import sys
import random

from PySide6 import QtWidgets, QtCore, QtGui

import stream

class VideoWorker(QtCore.QObject):
    frame_ready = QtCore.Signal(QtGui.QImage)

    def update_frame(self):
        parsed_frames = []
        for parsed_frame in parsed_frames:
            decoded_frames = CODEC.decode(parsed_frame)
            for decoded_frame in decoded_frames:
                image = decoded_frame.to_ndarray(format='bgr24')
                qimage = QtGui.QImage(image, 854, 480, QtGui.QImage.Format.Format_BGR888)
                self.frame_ready.emit(qimage.copy())

class VideoStream(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wii U Gamepad Stream")
        self.setFixedSize(854, 480)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        self.label = QtWidgets.QLabel("No video source available.", self)
        self.worker = VideoWorker()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)

        self.show()
        self.drag_pos = None

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        else:
            self.drag_pos = None

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

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
        self.thread = QtCore.QThread()
        self.output_window = VideoStream()
        self.output_window.worker.moveToThread(self.thread)
        self.thread.started.connect(self.output_window.worker.update_frame)
        self.output_window.worker.frame_ready.connect(
            lambda qimage: self.label.setPixmap(QtGui.QPixmap.fromImage(qimage))
        )
        self.thread.start()

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Wii U Gamepad Monitor")
        self.container = MainContainer()
        self.setCentralWidget(self.container)

    def closeEvent(self, event):
        if self.container.output_window:
            self.container.thread.quit()
            self.container.output_window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Main()
    widget.resize(1000, 1000)
    widget.show()

    sys.exit(app.exec())