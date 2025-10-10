import sys

from PySide6 import QtWidgets, QtCore, QtGui, QtNetwork

INTERFACE_NAME = 'tun0'
VIDEO_PORT = 50120

class VideoWorker(QtCore.QObject):
    frame_ready = QtCore.Signal(QtGui.QImage)

    def __init__(self):
        super().__init__()
        self.socket = QtNetwork.QUdpSocket()
        ip = VideoWorker.get_interface_ip()
        if ip:
            self.socket.bind(ip, VIDEO_PORT)
            print('Successfully setup socket')
        else:
            print('Failed to setup socket')
        self.socket.readyRead.connect(self.update_frame)

    def update_frame(self):
        parsed_frames = []
        for parsed_frame in parsed_frames:
            decoded_frames = CODEC.decode(parsed_frame)
            for decoded_frame in decoded_frames:
                image = decoded_frame.to_ndarray(format='bgr24')
                qimage = QtGui.QImage(image, 854, 480, QtGui.QImage.Format.Format_BGR888)
                self.frame_ready.emit(qimage.copy())

    def get_interface_ip():
        interface = QtNetwork.QNetworkInterface.interfaceFromName(INTERFACE_NAME)
        if interface.isValid():
            for entry in interface.addressEntries():
                return entry.ip()

class VideoStream(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wii U Gamepad Stream")
        self.setFixedSize(854, 480)
        self.setWindowFlag(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.label = QtWidgets.QLabel("No video source available.", self)
        self.worker = VideoWorker()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)

        self.show()
        self.drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

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
            self.container.output_window.worker.socket.close()
            self.container.output_window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = Main()
    widget.resize(1000, 1000)
    widget.show()

    sys.exit(app.exec())