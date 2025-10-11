import sys
import subprocess
import av
import cv2
import time

INTERFACE = 'wlp0s20u4'
CHANNEL = 40

UDP_PORT = 50020
TSHARK_PATH = '/run/current-system/sw/bin/tshark'

# Put wireless adapter in monitor mode
def setup_monitor_mode():
    subprocess.run(f'sudo ip link set {INTERFACE} down'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {INTERFACE} set type monitor'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {INTERFACE} set monitor fcsfail otherbss'.split(' '), check=True)
    subprocess.run(f'sudo ip link set {INTERFACE} up'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {INTERFACE} set channel {CHANNEL}'.split(' '), check=True)

# Setup H.264 decoder
def setup_codec():
    global FRAME_START, I_SLICE_HEADER, P_SLICE_HEADER, CODEC

    FRAME_START = bytes([0x00, 0x00, 0x00, 0x01])
    SPS_HEADER = bytes([0x67, 0x64, 0x00, 0x20, 0xac, 0x2b, 0x40, 0x6c, 0x1e, 0xf3, 0x68])
    PPS_HEADER = bytes([0x68, 0xEE, 0x06, 0x0C, 0xE8])
    I_SLICE_HEADER = bytes([0x25, 0xb8, 0x04, 0xff])
    P_SLICE_HEADER = bytes([0x21, 0xe0, 0x03, 0xff])

    CODEC = av.CodecContext.create('h264', 'r')
    parameter_sets = CODEC.parse(FRAME_START + SPS_HEADER + FRAME_START + PPS_HEADER)

# Helper functions
def get_sequence_num(payload):
    return payload[1] + ((payload[0] & 0x03) << 8)

def is_i_frame(payload):
    return payload[8] == 0x80

def is_frame_start(payload):
    return bool(payload[2] >> 6 & 1)

def is_frame_end(payload):
    return bool(payload[2] >> 4 & 1)

def get_headers(payload, frame_num):
    if is_i_frame(payload):
        # print("I frame sent")
        return FRAME_START + I_SLICE_HEADER
    else:
        return FRAME_START + bytes([P_SLICE_HEADER[0], P_SLICE_HEADER[1] | (frame_num >> 3), P_SLICE_HEADER[2] | (frame_num << 5) & 0xff, P_SLICE_HEADER[3]])

def get_safe_payload(payload):
    safe_payload = payload[16:18]
    for i in range(18, len(payload)):
        if payload[i] < 3 and safe_payload[-1] == 0 and safe_payload[-2] == 0:
            #print("emulation prevention")
            safe_payload += bytes([3])
        safe_payload += bytes([payload[i]])
    return safe_payload

def show_image(parsed_frames):
    for parsed_frame in parsed_frames:
        decoded_frames = CODEC.decode(parsed_frame)
        for decoded_frame in decoded_frames:
            image = decoded_frame.to_ndarray(format='bgr24')
            #print("image")
            cv2.imshow('Video Stream', image)
            if cv2.waitKey(1) & 0xff == ord('q'):
                return 1
    return 0

count = 0
def print_count(output, max):
    global count
    if max == count:
        return
    print(output)
    count +=1

def get_bits_int(x, start, end=None):
    if end == None:
        end = start + 1
    n = 0
    for i in range(start, end):
        n *= 2
        n += min(1, x[i//8] & 2**(7-i%8))
    return n

def print_header(temp):
    # print(temp.hex())
    output = f'magic: {get_bits_int(temp, 0, 4)} \n'
    output += f'packet type: {get_bits_int(temp, 4, 6)} \n'
    output += f'sequence number: {get_bits_int(temp, 6, 16)} \n'
    output += f'init flag: {get_bits_int(temp, 16)} \n'
    output += f'frame begin flag: {get_bits_int(temp, 17)} \n'
    output += f'chunk end flag: {get_bits_int(temp, 18)} \n'
    output += f'frame end flag: {get_bits_int(temp, 19)} \n'
    output += f'timestamp present flag: {get_bits_int(temp, 20)} \n'
    output += f'payload size: {get_bits_int(temp, 21, 32)} \n'
    output += f'timestamp: {get_bits_int(temp, 32, 64)} \n'
    return output + "\n"

# main
def stream(pcap_file):
    if pcap_file:
        capture_command = ['tshark', '-r', f'{pcap_file}', '-o', 'wlan.enable_decryption:TRUE', '-Y', f'udp.port=={UDP_PORT}', '-T', 'fields', '-e', 'data', '-l']
    else:
        setup_monitor_mode()
        capture_command = ['tshark', '-i', f'{INTERFACE}', '-o', 'wlan.enable_decryption:TRUE', '-Y', f'udp.port=={UDP_PORT}', '-T', 'fields', '-e', 'data', '-l']

    setup_codec()

    with subprocess.Popen(capture_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1) as proc:
        print('processing packets')

        frame_num = -1
        prev_sequence_num = 0
        gamepad_dropped_packet_count = 0
        misc_dropped_packet_count = 0
        monitor_dropped_packet_count = 0

        MAX_FRAME_NUM = 2**10
        DROPPED_PACKET_INTERVAL = 100
        
        for line in proc.stdout:
            payload = bytes.fromhex(line)
            # print('here')

            if not (is_i_frame(payload) or frame_num >= 0):
                continue

            if get_sequence_num(payload) != (prev_sequence_num + 1) % MAX_FRAME_NUM:
                print(f'gamepad: {gamepad_dropped_packet_count}')
                print(f'monitor: {monitor_dropped_packet_count}')
                print(f'misc: {misc_dropped_packet_count}')
                if get_sequence_num(payload) == prev_sequence_num:
                    gamepad_dropped_packet_count += 1
                    continue
                elif (get_sequence_num(payload) - prev_sequence_num) % MAX_FRAME_NUM < DROPPED_PACKET_INTERVAL:
                    monitor_dropped_packet_count += 1
                else:
                    misc_dropped_packet_count += 1
                    print(f'{get_sequence_num(payload)} -> {prev_sequence_num}')
            prev_sequence_num = get_sequence_num(payload)

            if is_frame_start(payload):
                parsed_frames = CODEC.parse(get_headers(payload, frame_num))
            else:
                parsed_frames = []

            CODEC.parse(get_safe_payload(payload))

            if (show_image(parsed_frames)):
                break

            if is_frame_end(payload):
                frame_num += 1
                frame_num %= 256
                # print(frame_num)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python stream.py <input.pcap>")
        sys.exit(1)
    pcap_file = sys.argv[1] if len(sys.argv) == 2 else None
    stream(pcap_file)