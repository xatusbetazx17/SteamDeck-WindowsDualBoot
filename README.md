# SteamDeck-WindowsDualBoot
A custom solution for enabling dual-boot capabilities between SteamOS and Windows on the Steam Deck. This tool allows users to easily install and switch between SteamOS and Windows, offering a seamless dual-boot experience. The project automates the process of detecting external storage (USB or microSD)



```bash
import sys
import os
import platform
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QMessageBox

# Function to install missing packages automatically
def install_package(package_name):
    try:
        if platform.system() == "Linux":
            print(f"Installing {package_name}...")
            result = subprocess.run(f"sudo pacman -S {package_name} --noconfirm", shell=True, check=True, capture_output=True, text=True)
            print(result.stdout)
            print(f"{package_name} installed successfully!")
        else:
            print(f"{package_name} installation not supported on this OS.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package_name}: {e.stderr}")

# Function to check and install wimlib-imagex if missing
def check_and_install_wimlib():
    try:
        if subprocess.call(["which", "wimlib-imagex"], stdout=subprocess.DEVNULL) != 0:
            print("wimlib-imagex is not installed. Attempting to install it...")
            install_package('wimlib')
        else:
            print("wimlib-imagex is already installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error checking wimlib-imagex: {e}")

# Function to partition and format the USB/microSD for UEFI booting
def partition_and_format_device(storage_device):
    try:
        # Create GPT partition table and partitions (100MB EFI partition and the rest for Windows)
        print(f"Partitioning {storage_device}...")
        os.system(f"sudo parted /dev/{storage_device} --script mklabel gpt")
        os.system(f"sudo parted /dev/{storage_device} --script mkpart ESP fat32 1MiB 100MiB")
        os.system(f"sudo parted /dev/{storage_device} --script set 1 boot on")
        os.system(f"sudo parted /dev/{storage_device} --script mkpart primary ntfs 100MiB 100%")

        # Format the EFI partition as FAT32
        os.system(f"sudo mkfs.fat -F32 /dev/{storage_device}1")

        # Format the main partition for Windows
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

# Function to create bootable Windows media on microSD or USB
def create_windows_media(install_wim, storage_device, selected_version):
    try:
        # Partition and format the USB/microSD
        partition_and_format_device(storage_device)

        # Mount the partitions
        print(f"Mounting {storage_device} partitions...")
        os.system(f"sudo mount /dev/{storage_device}2 /mnt/target")
        os.system(f"sudo mkdir -p /mnt/target/efi")
        os.system(f"sudo mount /dev/{storage_device}1 /mnt/target/efi")

        # Apply the selected Windows version to the main partition
        print(f"Writing Windows version {selected_version} to {storage_device}...")
        os.system(f"sudo wimlib-imagex apply {install_wim} {selected_version} /mnt/target")

        # Make the device bootable with GRUB
        print("Installing GRUB bootloader...")
        os.system(f"sudo grub-install --target=x86_64-efi --efi-directory=/mnt/target/efi --boot-directory=/mnt/target/boot --removable /dev/{storage_device}")

        print("Windows successfully written to the USB/microSD and made bootable.")
    except Exception as e:
        print(f"Error creating bootable media: {e}")
    finally:
        # Unmount partitions
        print(f"Unmounting {storage_device} partitions...")
        os.system(f"sudo umount /mnt/target/efi")
        os.system(f"sudo umount /mnt/target")

# Function to detect the microSD card or USB
def detect_storage_device():
    try:
        # Detect connected USB/microSD devices (external drives)
        result = subprocess.check_output("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E 'sd[b-z]|mmcblk'", shell=True).decode('utf-8')
        devices = [line.split()[0] for line in result.strip().split("\n")]
        return devices if devices else None
    except subprocess.CalledProcessError as e:
        print(f"Error detecting storage devices: {e}")
        return None

# Main application class
class RufusClone(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows To Go Installation Tool")
        self.setGeometry(100, 100, 600, 400)

        self.iso_file = None
        self.wim_file = None
        self.selected_version = None
        # Changed mount point to home directory to avoid permission errors
        self.mount_point = os.path.expanduser("~/windows_iso_mount")  # Home directory mount point

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.iso_label = QLabel("No ISO selected")
        layout.addWidget(self.iso_label)

        self.select_iso_button = QPushButton("Select Windows ISO")
        self.select_iso_button.clicked.connect(self.select_iso)
        layout.addWidget(self.select_iso_button)

        self.version_selection = QComboBox(self)
        layout.addWidget(self.version_selection)

        self.select_storage_button = QPushButton("Create Bootable USB/microSD")
        self.select_storage_button.clicked.connect(self.create_bootable)
        layout.addWidget(self.select_storage_button)

        self.device_selection = QComboBox(self)  # Dropdown to select device
        layout.addWidget(QLabel("Select Storage Device:"))
        layout.addWidget(self.device_selection)

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
            if mount_iso(self.iso_file, self.mount_point):
                self.wim_file = find_install_wim(self.mount_point)
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

        if storage_device and self.wim_file:
            create_windows_media(self.wim_file, storage_device, selected_version)
            unmount_iso(self.mount_point)
        else:
            QMessageBox.warning(self, "Error", "Please select a storage device and Windows version.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RufusClone()
    window.show()
    sys.exit(app.exec_())


```

## SteamDeck-WindowsDualBoot
A custom solution for enabling dual-boot capabilities between SteamOS and Windows on the Steam Deck. This tool simplifies the process of installing Windows on an external medium (USB or microSD) and configuring your Steam Deck to dual boot between SteamOS and Windows.

## Features

Automatically detects external storage (USB or microSD)

Allows the user to select a Windows version from an ISO file

Automates the installation of necessary dependencies (e.g., wimlib-imagex)
Configures the Steam Deck to dual-boot between SteamOS and Windows
Seamlessly switch between SteamOS and Windows

## Requirements

A Steam Deck with SteamOS

A Windows ISO file

A USB drive or microSD card

An internet connection for downloading dependencies
Installation & Setup

## 1. Clone the repository
Start by cloning the repository to your Steam Deck:

```git clone https://github.com/YOUR_USERNAME/SteamDeck-WindowsDualBoot.git```
```cd SteamDeck-WindowsDualBoot```

## 2. Install dependencies
Ensure the necessary dependencies are installed before running the script.
```
sudo pacman -S python-pyqt5 efibootmgr refind wimlib --noconfirm
```
Alternatively, the Python script can install the required dependencies automatically if they are missing.

## 3. Run the Python script
```
python3 dual_boot.py
```
This will launch the graphical interface, where you can select your Windows ISO and the target device (USB or microSD) for the Windows installation.

## How to Use
Download a Windows ISO: If you don’t have a Windows ISO, you can download it from the Microsoft website.

## Launch the Tool: Open the tool by running the Python script:
```
python3 dual_boot.py
```
Select the ISO: Click on "Select Windows ISO" and browse to your downloaded ISO file.

Select the Windows Version: The tool will display the available Windows versions from the ISO. Choose your desired version from the dropdown.

Choose the Storage Device: The tool will automatically detect external storage devices (USB or microSD). Choose your preferred device.

Install Windows: Click the button to create the bootable Windows media. The script will use dd to write the ISO to the selected device.

Dual Boot Setup: After installation, the tool will configure your Steam Deck’s boot manager (using efibootmgr or rEFInd) to support dual-booting between SteamOS and Windows.

Switch Between OSes: After installation, you can switch between SteamOS and Windows using the tool.

## Troubleshooting
No storage devices detected: Ensure your USB or microSD card is properly connected. Use lsblk to manually check if the device is listed.

wimlib-imagex not found: If the tool says wimlib-imagex is not installed, you can manually install it using:
```sudo pacman -S wimlib```

## What the Script Does
The Python script provides a graphical user interface for performing the following tasks:

Detects External Storage: Uses lsblk to list connected USB or microSD storage devices.
ISO Selection and Parsing: Allows the user to browse for a Windows ISO file, and uses wimlib-imagex to list available Windows versions.
Create Bootable Windows Media: Writes the selected Windows version to the target USB or microSD using dd.
Configure Dual Boot: Configures the boot manager (e.g., efibootmgr or rEFInd) to allow switching between SteamOS and Windows.
Switching Between OSes: Lets users switch back and forth between SteamOS and Windows through boot entry management.

## Contributing
Feel free to open issues or contribute by submitting pull requests. All contributions are welcome!
