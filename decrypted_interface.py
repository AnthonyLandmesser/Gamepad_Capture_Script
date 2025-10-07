import os
import subprocess

PHYSICAL_INTERFACE = 'wlp0s20u4'
CHANNEL = 157

UDP_PORT = 50020
CAPTURE_COMMAND = f'tshark -i {PHYSICAL_INTERFACE} -o wlan.enable_decryption:TRUE -Y udp.port=={UDP_PORT} -T fields -e data -l'.split(' ')

def create_tunnel():
    tunnel = open()

# Put wireless interface in monitor mode
def setup_physical_interface():
    subprocess.run(f'sudo ip link set {PHYSICAL_INTERFACE} down'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set type monitor'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set monitor fcsfail otherbss'.split(' '), check=True)
    subprocess.run(f'sudo ip link set {PHYSICAL_INTERFACE} up'.split(' '), check=True)
    subprocess.run(f'sudo iw dev {PHYSICAL_INTERFACE} set channel {CHANNEL}'.split(' '), check=True)

# Main
def create_decrypted_interface():
    setup_physical interface()
    create_virtual_interface()
    tshark_passthrough()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root.")
    else:
        create_decrypted_interface()