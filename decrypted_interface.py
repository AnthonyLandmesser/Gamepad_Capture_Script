import os
import subprocess
import fcntl
import struct
import sys

from scapy.all import IP, UDP, Raw

PHYSICAL_INTERFACE = 'wlp0s20u4'
CHANNEL = 40

VIRTUAL_INTERFACE = 'tun0'
IP_ADDRESS = '10.0.0.1/24'

TUN_SET_INTERFACE_FLAGS = 0x400454CA
INTERFACE_REQUEST_FLAGS = 0x1001
UDP_PORT = 50020

# Put wireless interface in monitor mode
def setup_physical_interface():
    subprocess.run(f'sudo ip link set {PHYSICAL_INTERFACE} down'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set type monitor'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set monitor fcsfail otherbss'.split(' '), check=True)
    subprocess.run(f'sudo ip link set {PHYSICAL_INTERFACE} up'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set channel {CHANNEL}'.split(' '), check=True)

def create_virtual_interface():
    subprocess.run(f'sudo ip link set {VIRTUAL_INTERFACE} down'.split(' '), check=True)
    subprocess.run(f'sudo ip tuntap add dev {VIRTUAL_INTERFACE} mode tun'.split(' '), check=False)
    subprocess.run(f'sudo ip addr add {IP_ADDRESS} dev {VIRTUAL_INTERFACE}'.split(' '), check=False)
    subprocess.run(f'sudo ip link set {VIRTUAL_INTERFACE} up'.split(' '), check=True)

    tunnel = os.open('/dev/net/tun', os.O_RDWR)
    interface_request = struct.pack('16sH', VIRTUAL_INTERFACE.encode('utf-8'), INTERFACE_REQUEST_FLAGS)
    fcntl.ioctl(tunnel, TUN_SET_INTERFACE_FLAGS, interface_request)
    return tunnel

def tshark_passthrough(tunnel, pcap_file):
    if pcap_file:
        capture_command = f'tshark -r {pcap_file} -o wlan.enable_decryption:TRUE -Y udp.port=={UDP_PORT} -T fields -e data -l'.split(' ')
    else:
        capture_command = f'tshark -i {PHYSICAL_INTERFACE} -o wlan.enable_decryption:TRUE -Y udp.port=={UDP_PORT} -T fields -e data -l'.split(' ')

    while True:
        with subprocess.Popen(capture_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1) as proc:
            print('waiting for packets')
            sending = False
            for payload in proc.stdout:
                if not sending:
                    sending = True
                    print('sending packets')
                packet = IP(src='192.168.1.10', dst='192.168.1.11', ttl=64)/UDP(sport=50020, dport=50120)/Raw(payload.encode('utf-8'))
                os.write(tunnel, bytes(packet))

# Main
def create_decrypted_interface(pcap_file):
    if not pcap_file:
        setup_physical_interface()
    tunnel = create_virtual_interface()
    tshark_passthrough(tunnel, pcap_file)

if __name__ == "__main__":
    if os.geteuid() == 0:
        print("This script must not be run with sudo.")
    else:
        pcap_file = sys.argv[1] if len(sys.argv) == 2 else None
        create_decrypted_interface(pcap_file)