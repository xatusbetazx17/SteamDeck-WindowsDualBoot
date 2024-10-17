import sys
import os
import platform
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QSpinBox, QMessageBox, QCheckBox

# Function to install missing packages automatically
def install_package(package_name):
    try:
        if platform.system() == "Linux":
            # Check for package manager and install package accordingly
            if subprocess.run("which apt", shell=True, stdout=subprocess.PIPE).returncode == 0:
                result = subprocess.run(f"sudo apt install {package_name} -y", shell=True, check=True, capture_output=True, text=True)
            elif subprocess.run("which pacman", shell=True, stdout=subprocess.PIPE).returncode == 0:
                result = subprocess.run(f"sudo pacman -S {package_name} --noconfirm", shell=True, check=True, capture_output=True, text=True)
            elif subprocess.run("which dnf", shell=True, stdout=subprocess.PIPE).returncode == 0:
                result = subprocess.run(f"sudo dnf install {package_name} -y", shell=True, check=True, capture_output=True, text=True)
            else:
                print("No supported package manager found.")
                return
            print(result.stdout)
            print(f"{package_name} installed successfully!")
        else:
            print(f"{package_name} installation not supported on this OS.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package_name}: {e.stderr}")

# Function to check if wimlib is installed
def check_and_install_wimlib():
    if subprocess.call(["which", "wimlib-imagex"], stdout=subprocess.DEVNULL) != 0:
        print("wimlib-imagex is not installed. Attempting to install it...")
        install_package('wimlib')
    else:
        print("wimlib-imagex is already installed.")

# Function to install Ventoy
def install_ventoy():
    try:
        ventoy_url = "https://github.com/ventoy/Ventoy/releases/latest/download/ventoy-1.0.82-linux.tar.gz"
        ventoy_tar = "ventoy.tar.gz"
        ventoy_dir = os.path.expanduser("~/ventoy")

        if not os.path.exists(ventoy_dir):
            print("Downloading and installing Ventoy...")
            os.system(f"wget {ventoy_url} -O {ventoy_tar}")
            os.system(f"tar -xzf {ventoy_tar} -C ~/")
        else:
            print("Ventoy is already installed.")
    except Exception as e:
        print(f"Error installing Ventoy: {e}")

# Function to partition and format the USB/microSD based on user input
def partition_and_format_device(storage_device, partition_size, is_primary):
    try:
        print(f"Partitioning {storage_device}...")
        # Partition the storage device
        os.system(f"sudo parted /dev/{storage_device} --script mklabel gpt")
        os.system(f"sudo parted /dev/{storage_device} --script mkpart ESP fat32 1MiB 100MiB")
        os.system(f"sudo parted /dev/{storage_device} --script set 1 boot on")

        # User input size for partitioning
        if partition_size:
            end_size = f"{partition_size}MiB"
        else:
            end_size = "100%"

        part_type = "primary" if is_primary else "logical"
        os.system(f"sudo parted /dev/{storage_device} --script mkpart {part_type} ntfs 100MiB {end_size}")

        # Format the partitions
        os.system(f"sudo mkfs.fat -F32 /dev/{storage_device}1")
        os.system(f"sudo mkfs.ntfs -f /dev/{storage_device}2")
        print(f"Partitioning and formatting complete for {storage_device}.")
    except Exception as e:
        print(f"Error partitioning device: {e}")

# Function to mount the ISO and locate the WIM/ESD file
def mount_iso(iso_file, mount_point):
    try:
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        subprocess.run(f"sudo mount -o loop {iso_file} {mount_point}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error mounting ISO: {e}")
        return False

# Function to unmount the ISO
def unmount_iso(mount_point):
    try:
        subprocess.run(f"sudo umount {mount_point}", shell=True, check=True)
        print("ISO unmounted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error unmounting ISO: {e}")

# Function to find the install.wim or install.esd file in the mounted ISO
def find_install_wim(mount_point):
    sources_dir = os.path.join(mount_point, "sources")
    try:
        install_file = next(f for f in os.listdir(sources_dir) if f.startswith("install.") and f.endswith(("wim", "esd")))
        return os.path.join(sources_dir, install_file)
    except StopIteration:
        print("No install.wim or install.esd file found.")
        return None

# Function to list available Windows versions from the WIM/ESD file using wimlib
def list_windows_versions(wim_file):
    try:
        check_and_install_wimlib()  # Ensure wimlib-imagex is installed
        output = subprocess.check_output(f"wimlib-imagex info {wim_file}", shell=True).decode('utf-8')
        versions = [line.split(":")[1].strip() for line in output.split("\n") if "Name:" in line]
        return versions
    except subprocess.CalledProcessError as e:
        print(f"Error listing Windows versions: {e}")
        return []

# Function to install Ventoy on the selected USB drive
def install_ventoy_on_device(storage_device):
    try:
        print(f"Installing Ventoy on {storage_device}...")
        os.system(f"sudo ~/ventoy/Ventoy2Disk.sh -i /dev/{storage_device}")
        print("Ventoy installation complete.")
    except Exception as e:
        print(f"Error installing Ventoy: {e}")

# Function to create bootable Windows media with Ventoy
def create_windows_media_with_ventoy(storage_device, iso_file, selected_version, partition_size, is_primary):
    try:
        # Partition and format the USB/microSD
        partition_and_format_device(storage_device, partition_size, is_primary)

        # Install Ventoy
        install_ventoy_on_device(storage_device)

        # Apply the selected Windows version using wimlib-imagex
        print(f"Writing Windows version {selected_version} to the device...")
        os.system(f"sudo wimlib-imagex apply {iso_file} {selected_version} /mnt/target")
        print("Windows successfully copied and Ventoy installed.")
    except Exception as e:
        print(f"Error creating bootable media with Ventoy: {e}")

# Function to detect the microSD card or USB
def detect_storage_device():
    try:
        result = subprocess.check_output("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E 'sd[b-z]|mmcblk'", shell=True).decode('utf-8')
        devices = [line.split()[0] for line in result.strip().split("\n")]
        return devices if devices else None
    except subprocess.CalledProcessError as e:
        print(f"Error detecting storage devices: {e}")
        return None

# Main application class
class RufusCloneVentoy(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows To Go Installation Tool with Ventoy")
        self.setGeometry(100, 100, 600, 400)

        self.iso_file = None
        self.partition_size = 0  # Default size for partition
        self.is_primary = True  # Default to primary partition
        self.wim_file = None  # Store the install.wim file
        self.selected_version = None  # Store selected Windows version

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Label for selected ISO
        self.iso_label = QLabel("No ISO selected")
        layout.addWidget(self.iso_label)

        # Button to select Windows ISO
        self.select_iso_button = QPushButton("Select Windows ISO")
        self.select_iso_button.clicked.connect(self.select_iso)
        layout.addWidget(self.select_iso_button)

        # ComboBox to select Windows version
        self.version_selection = QComboBox(self)
        layout.addWidget(QLabel("Select Windows Version:"))
        layout.addWidget(self.version_selection)

        # Partition size input
        self.partition_size_input = QSpinBox(self)
        self.partition_size_input.setMinimum(100)  # Minimum 100MB for partition
        self.partition_size_input.setMaximum(100000)  # Max size limit
        self.partition_size_input.setValue(4096)  # Default to 4GB
        layout.addWidget(QLabel("Partition Size (MB):"))
        layout.addWidget(self.partition_size_input)

        # Option for primary or logical partition
        self.is_primary_checkbox = QCheckBox("Primary Partition")
        self.is_primary_checkbox.setChecked(True)
        layout.addWidget(self.is_primary_checkbox)

        # Dropdown to select storage device
        self.device_selection = QComboBox(self)
        layout.addWidget(QLabel("Select Storage Device:"))
        layout.addWidget(self.device_selection)

        # Button to create bootable USB/microSD
        self.create_bootable_button = QPushButton("Create Bootable USB/microSD with Ventoy")
        self.create_bootable_button.clicked.connect(self.create_bootable)
        layout.addWidget(self.create_bootable_button)

        self.refresh_storage_devices()

        self.setLayout(layout)

    def refresh_storage_devices(self):
        devices = detect_storage_device()
        if devices:
            self.device_selection.clear()
            self.device_selection.addItems(devices)
        else:
            QMessageBox.warning(self, "Error", "No storage devices detected. Please insert a USB or microSD card.")

    def select_iso(self):
        self.iso_file, _ = QFileDialog.getOpenFileName(self, "Select Windows ISO", "", "ISO Files (*.iso)")
        if self.iso_file:
            self.iso_label.setText(f"Selected ISO: {self.iso_file}")
            mount_point = os.path.expanduser("~/windows_iso_mount")
            if mount_iso(self.iso_file, mount_point):
                self.wim_file = find_install_wim(mount_point)
                if self.wim_file:
                    versions = list_windows_versions(self.wim_file)
                    self.version_selection.clear()
                    self.version_selection.addItems(versions)
                else:
                    QMessageBox.warning(self, "Error", "No install.wim or install.esd file found in the ISO.")
        else:
            self.iso_label.setText("No ISO file selected.")

    def create_bootable(self):
        selected_version = self.version_selection.currentText()
        storage_device = self.device_selection.currentText()
        partition_size = self.partition_size_input.value()
        is_primary = self.is_primary_checkbox.isChecked()

        if storage_device and self.iso_file:
            create_windows_media_with_ventoy(storage_device, self.wim_file, selected_version, partition_size, is_primary)
            unmount_iso(os.path.expanduser("~/windows_iso_mount"))
        else:
            QMessageBox.warning(self, "Error", "Please select a storage device and Windows version.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RufusCloneVentoy()
    window.show()
    sys.exit(app.exec_())
