# SteamDeck-WindowsDualBoot
A custom solution for enabling dual-boot capabilities between SteamOS and Windows on the Steam Deck. This tool allows users to easily install and switch between SteamOS and Windows, offering a seamless dual-boot experience. The project automates the process of detecting external storage (USB or microSD)



```bash
import sys
import os
import platform
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QSpinBox, QMessageBox, QCheckBox

# Function to install missing packages automatically using pacman
def install_package_pacman(package_name):
    try:
        if platform.system() == "Linux":
            # Check if the package is installed using pacman (Arch-based system)
            print(f"Checking if {package_name} is installed via pacman...")
            result = subprocess.run(f"pacman -Q {package_name}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:  # If package is not installed
                print(f"{package_name} is not installed. Installing...")
                subprocess.run(f"sudo pacman -S {package_name} --noconfirm", shell=True, check=True)
                print(f"{package_name} installed successfully!")
            else:
                print(f"{package_name} is already installed.")
        else:
            print(f"{package_name} installation is not supported on this OS.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package_name}: {e.stderr}")

# Function to install missing packages from chaotic AUR using pacman
def install_package_chaotic_aur(package_name):
    try:
        if platform.system() == "Linux":
            # Check if the package is installed using pacman (Arch-based system)
            print(f"Checking if {package_name} is installed via chaotic AUR...")
            result = subprocess.run(f"pacman -Q {package_name}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:  # If package is not installed
                print(f"{package_name} is not installed. Installing from chaotic AUR...")
                subprocess.run(f"sudo pacman -S {package_name} --noconfirm", shell=True, check=True)
                print(f"{package_name} installed successfully from chaotic AUR!")
            else:
                print(f"{package_name} is already installed.")
        else:
            print(f"{package_name} installation is not supported on this OS.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing {package_name}: {e.stderr}")

# Function to check if PyQt5 is installed and install it if necessary
def check_and_install_pyqt5():
    try:
        import PyQt5
        print("PyQt5 is already installed.")
    except ImportError:
        print("PyQt5 is not installed. Installing PyQt5 via pacman...")
        install_package_pacman('pyqt5')

# Function to check if WoeUSB is installed from Chaotic AUR and install it if necessary
def check_and_install_woeusb():
    try:
        # Check if woeusb command is available
        subprocess.run("woeusb --help", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("WoeUSB is already installed.")
    except subprocess.CalledProcessError:
        print("WoeUSB is not installed. Installing woeusb from chaotic AUR...")
        install_package_chaotic_aur('woeusb')

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

# Check if PyQt5 is installed, and install if necessary
check_and_install_pyqt5()
# Check if WoeUSB is installed, and install if necessary
check_and_install_woeusb()

# Import PyQt5 after ensuring it's installed
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QSpinBox, QMessageBox, QCheckBox

# Main application class
class RufusCloneWoeUSB(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows To Go Installation Tool with WoeUSB")
        self.setGeometry(100, 100, 600, 400)

        self.iso_file = None
        self.partition_size = 0  # Default size for partition
        self.is_primary = True  # Default to primary partition
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
        self.create_bootable_button = QPushButton("Create Bootable USB/microSD with WoeUSB")
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
        else:
            self.iso_label.setText("No ISO file selected.")

    def create_bootable(self):
        storage_device = self.device_selection.currentText()
        partition_size = self.partition_size_input.value()
        is_primary = self.is_primary_checkbox.isChecked()

        if storage_device and self.iso_file:
            try:
                # Create a bootable USB using WoeUSB
                device_path = f"/dev/{storage_device}"
                print(f"Creating bootable USB using WoeUSB on device: {device_path}")
                subprocess.run(f"sudo woeusb --device {self.iso_file} {device_path}", shell=True, check=True)
                QMessageBox.information(self, "Success", "Bootable USB created successfully with WoeUSB.")
            except subprocess.CalledProcessError as e:
                print(f"Error creating bootable USB: {e}")
                QMessageBox.warning(self, "Error", "Failed to create bootable USB. Please check the terminal for details.")
        else:
            QMessageBox.warning(self, "Error", "Please select a storage device and Windows ISO.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RufusCloneWoeUSB()
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
