import subprocess
import av
import cv2

INTERFACE = 'wlp0s20u4'
CHANNEL = 157

UDP_PORT = 50020
TSHARK_PATH = '/run/current-system/sw/bin/tshark'

# Put wireless adapter in monitor mode
subprocess.run(['sudo', 'airmon-ng', 'check', 'kill'], check=True)
subprocess.run(['sudo', 'airmon-ng', 'start', f'{INTERFACE}', f'{CHANNEL}'], check=True)
subprocess.run(['sudo', 'iw', 'dev', f'{INTERFACE}', 'set', 'monitor', 'fcsfail'], check=True)

# Setup H.264 decoder
FRAME_START = bytes([0x00, 0x00, 0x00, 0x01])
SPS_HEADER = bytes([0x67, 0x64, 0x00, 0x20, 0xac, 0x2b, 0x40, 0x6c, 0x1e, 0xf3, 0x68])
PPS_HEADER = bytes([0x68, 0xEE, 0x06, 0x0C, 0xE8])
I_SLICE_HEADER = bytes([0x25, 0xb8, 0x04, 0xff])
P_SLICE_HEADER = bytes([0x21, 0xe0, 0x03, 0xff])

codec = av.CodecContext.create('h264', 'r')
parameter_sets = codec.parse(FRAME_START + SPS_HEADER + FRAME_START + PPS_HEADER)

# Capture UDP traffic
capture_command = ['tshark', '-i', f'{INTERFACE}', '-o', 'wlan.enable_decryption:TRUE', '-Y', f'udp.port=={UDP_PORT}', '-T', 'fields', '-e', 'data', '-l']

# Helper functions
def is_i_frame(payload):
    return payload[8] == 0x80

def is_frame_start(payload):
    return bool(payload[2] >> 6 & 1)

def is_frame_end(payload):
    return bool(payload[2] >> 4 & 1)

def get_headers(payload, frame_num):
    parsed_frames = []
    if is_frame_start(payload):
        if is_i_frame(payload):
            parsed_frames = codec.parse(FRAME_START + I_SLICE_HEADER)
            print("I frame sent")
        else:
            curr_header = bytes([P_SLICE_HEADER[0], P_SLICE_HEADER[1] | (frame_num >> 3), P_SLICE_HEADER[2], P_SLICE_HEADER[3] | (frame_num << 5) & 0xff])
            parsed_frames = codec.parse(FRAME_START + curr_header)
    return parsed_frames

def get_safe_payload(payload):
    safe_payload = payload[16:18]
    for i in range(18, len(payload)):
        if payload[i] < 3 and safe_payload[-1] == 0 and safe_payload[-2] == 0:
            print("emulation prevention")
            safe_payload += bytes([3])
        safe_payload += bytes([payload[i]])
    return safe_payload

def show_image(parsed_frames):
    for parsed_frame in parsed_frames:
        decoded_frames = codec.decode(parsed_frame)
        for decoded_frame in decoded_frames:
            image = decoded_frame.to_ndarray(format='bgr24')
            #print(image)
            cv2.imshow('Video Stream', image)
            if cv2.waitKey(1) & 0xff == ord('q'):
                return 1
    return 0

# main
def main():
    with subprocess.Popen(capture_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1) as proc:
        frame_num = 0
        go = False
        for line in proc.stdout:
            payload = bytes.fromhex(line)
            # print(payload)

            if not (is_i_frame(payload) or go):
                continue

            parsed_frames = get_headers(payload, frame_num)

            parsed_frames += codec.parse(get_safe_payload(payload))

            if (show_image(parsed_frames)):
                break

            if is_frame_end(payload):
                go = True
                frame_num += 1
                frame_num %= 256
                #print(frame_num)

if __name__ == "__main__":
    main()