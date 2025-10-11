import sys

from PySide6 import QtWidgets, QtCore, QtGui, QtNetwork
import av

INTERFACE_NAME = 'tun0'
VIDEO_PORT = 50120

class VideoWorker(QtCore.QObject):
    frame_ready = QtCore.Signal(QtGui.QImage)

    def __init__(self):
        super().__init__()

        self.setup_codec()

        self.frame_num = -1
        self.prev_sequence_num = 0
        self.gamepad_dropped_packet_count = 0
        self.misc_dropped_packet_count = 0
        self.monitor_dropped_packet_count = 0

        self.MAX_FRAME_NUM = 2**10
        self.DROPPED_PACKET_INTERVAL = 100

        self.socket = QtNetwork.QUdpSocket()
        ip = VideoWorker.get_interface_ip()
        if ip:
            self.socket.bind(ip, VIDEO_PORT)
            print('Successfully setup socket')
        else:
            print('Failed to setup socket')
        self.socket.readyRead.connect(self.update_frame)

    def update_frame(self):
        while self.socket.hasPendingDatagrams():
            payload = self.socket.readDatagram(self.socket.pendingDatagramSize())
            print(type(payload))

            if not (VideoWorker.is_i_frame(payload) or self.frame_num >= 0):
                continue

            if VideoWorker.get_sequence_num(payload) != (self.prev_sequence_num + 1) % self.MAX_FRAME_NUM:
                print(f'gamepad: {self.gamepad_dropped_packet_count}')
                print(f'monitor: {self.monitor_dropped_packet_count}')
                print(f'misc: {self.misc_dropped_packet_count}')
                if VideoWorker.get_sequence_num(payload) == self.prev_sequence_num:
                    self.gamepad_dropped_packet_count += 1
                    continue
                elif (VideoWorker.get_sequence_num(payload) - self.prev_sequence_num) % self.MAX_FRAME_NUM < self.DROPPED_PACKET_INTERVAL:
                    self.monitor_dropped_packet_count += 1
                else:
                    self.misc_dropped_packet_count += 1
                    print(f'{VideoWorker.get_sequence_num(payload)} -> {self.prev_sequence_num}')
            self.prev_sequence_num = VideoWorker.get_sequence_num(payload)

            if VideoWorker.is_frame_start(payload):
                parsed_frames = self.CODEC.parse(self.get_headers(payload))
            else:
                parsed_frames = []

            self.CODEC.parse(VideoWorker.get_safe_payload(payload))

            VideoWorker.show_image(parsed_frames)

            if VideoWorker.is_frame_end(payload):
                self.frame_num += 1
                self.frame_num %= 256

    def show_image(parsed_frames):
        for parsed_frame in parsed_frames:
            decoded_frames = self.CODEC.decode(parsed_frame)
            for decoded_frame in decoded_frames:
                image = decoded_frame.to_ndarray(format='bgr24')
                qimage = QtGui.QImage(image, 854, 480, QtGui.QImage.Format.Format_BGR888)
                self.frame_ready.emit(qimage.copy())
    
    def is_i_frame(payload):
        return payload[8] == 0x80

    def get_sequence_num(payload):
        return payload[1] + ((payload[0] & 0x03) << 8)

    def is_frame_start(payload):
        return bool(payload[2] >> 6 & 1)

    def get_headers(self, payload):
        if VideoWorker.is_i_frame(payload):
            return self.FRAME_START + self.I_SLICE_HEADER
        else:
            p_slice_header_final = bytes([
                P_SLICE_HEADER[0],
                P_SLICE_HEADER[1] | (frame_num >> 3),
                P_SLICE_HEADER[2] | (frame_num << 5) & 0xff,
                P_SLICE_HEADER[3],
            ])
            return self.FRAME_START + p_slice_header_final

    def setup_codec(self):
        self.FRAME_START = bytes([0x00, 0x00, 0x00, 0x01])
        self.SPS_HEADER = bytes([0x67, 0x64, 0x00, 0x20, 0xac, 0x2b, 0x40, 0x6c, 0x1e, 0xf3, 0x68])
        self.PPS_HEADER = bytes([0x68, 0xEE, 0x06, 0x0C, 0xE8])
        self.I_SLICE_HEADER = bytes([0x25, 0xb8, 0x04, 0xff])
        self.P_SLICE_HEADER = bytes([0x21, 0xe0, 0x03, 0xff])

        self.CODEC = av.CodecContext.create('h264', 'r')
        self.CODEC.parse(self.FRAME_START + self.SPS_HEADER + self.FRAME_START + self.PPS_HEADER)

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
        self.resize(1000, 1000)
        self.show()

    def closeEvent(self, event):
        if self.container.output_window:
            self.container.thread.quit()
            self.container.output_window.worker.socket.close()
            self.container.output_window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = Main()
    sys.exit(app.exec())