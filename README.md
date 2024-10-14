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

# Check if PyQt5 is installed, if not, install it
def install_pyqt5():
    if platform.system() == "Linux":
        print("Attempting to install PyQt5 on SteamOS (Linux)...")
        try:
            result = subprocess.run("sudo pacman -S python-pyqt5 --noconfirm", shell=True, check=True, capture_output=True, text=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error installing PyQt5 on SteamOS: {e.stderr}")
            print("Please try running the following command manually:")
            print("sudo pacman -S python-pyqt5")
    elif platform.system() == "Windows":
        print("Attempting to install PyQt5 on Windows...")
        try:
            result = subprocess.run("pip install PyQt5", shell=True, check=True, capture_output=True, text=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error installing PyQt5 on Windows: {e.stderr}")
            print("Please try running the following command manually:")
            print("pip install PyQt5")

# Check if PyQt5 is installed, if not, install it
try:
    from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QMessageBox
except ModuleNotFoundError as e:
    print("PyQt5 not found: ", e)
    install_pyqt5()

    # Try importing PyQt5 again after attempting installation
    try:
        from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog, QComboBox, QMessageBox
    except ModuleNotFoundError as e:
        print("PyQt5 installation failed. Please try to install it manually.")
        print(f"Error details: {e}")
        sys.exit(1)

# Function to detect the microSD card or USB
def detect_storage_device():
    try:
        # Filter for USB or microSD devices, exclude internal drives (like sda or nvme0)
        result = subprocess.check_output("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E 'sd[b-z]|mmcblk'", shell=True).decode('utf-8')
        devices = [line.split()[0] for line in result.strip().split("\n")]
        if devices:
            return devices
        else:
            print("No external storage device detected.")
            return None
    except subprocess.CalledProcessError:
        print("Error detecting storage devices.")
        return None

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

# Function to download Windows ISO
def download_windows_iso():
    download_url = "https://www.microsoft.com/en-us/software-download/windows11"
    print(f"Opening browser to download Windows ISO from: {download_url}")
    os.system(f"xdg-open {download_url}")  # Open browser to download the ISO manually

# Function to list available Windows versions from ISO (use wimlib)
def list_windows_versions(iso_file):
    try:
        check_and_install_wimlib()  # Ensure wimlib-imagex is installed
        # Use wimlib-imagex to list Windows versions
        cmd = f"wimlib-imagex info {iso_file}"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        versions = []
        for line in output.split('\n'):
            if "Name:" in line:
                version = line.split(":")[1].strip()
                versions.append(version)
        return versions
    except subprocess.CalledProcessError as e:
        print(f"Error reading Windows versions: {e.stderr}")
        return []

# Function to create bootable Windows media on microSD or USB
def create_windows_media(storage_device, iso_file, selected_version):
    if not iso_file:
        print("No ISO selected.")
        return

    print(f"Writing Windows ISO ({selected_version}) to {storage_device}...")
    os.system(f"sudo dd if={iso_file} of=/dev/{storage_device} bs=4M status=progress && sync")
    print(f"Windows ISO successfully written to {storage_device}")

# Define the main application class
class DualBootApp(QWidget):
    def __init__(self):
        super().__init__()

        # Setup window
        self.setWindowTitle("Steam Deck Dual Boot & Windows Installation")
        self.setGeometry(100, 100, 600, 400)

        # Detect the current OS
        self.os = platform.system()

        # Install necessary packages based on the OS
        self.install_dependencies()

        # Create UI elements
        self.status_label = QLabel(self)
        self.version_selection = QComboBox(self)
        self.device_selection = QComboBox(self)  # Dropdown for selecting the device
        self.iso_file = None
        self.setup_ui()

    def install_dependencies(self):
        """
        Install necessary dependencies based on the detected operating system.
        """
        if self.os == "Linux":
            print("Detected SteamOS (Linux). Installing necessary packages...")
            # Check if efibootmgr is installed
            if not self.is_package_installed('efibootmgr'):
                os.system("sudo pacman -S efibootmgr --noconfirm")

            # Optionally install rEFInd (for better boot management)
            if not self.is_package_installed('refind'):
                os.system("sudo pacman -S refind --noconfirm")

            # Handle systemd session management error
            try:
                os.system("sudo systemctl --user start steam.service || echo 'Already in Desktop Mode'")
            except Exception as e:
                print(f"Systemd session management error: {e}")
        elif self.os == "Windows":
            print("Detected Windows. Ensuring bcdedit and boot configurations...")
            try:
                subprocess.check_output(["bcdedit", "/enum"])
            except subprocess.CalledProcessError:
                print("Error: bcdedit not available or permission issue.")
                sys.exit(1)

    def is_package_installed(self, package_name):
        """
        Check if a package is installed on SteamOS (Linux).
        """
        try:
            result = subprocess.check_output(f"pacman -Q {package_name}", shell=True)
            return True if result else False
        except subprocess.CalledProcessError:
            return False

    def setup_ui(self):
        """
        Setup the UI based on the operating system.
        """
        layout = QVBoxLayout()

        if self.os == "Linux":
            self.status_label.setText("Currently on SteamOS")
            layout.addWidget(self.status_label)

            # Button to download Windows ISO
            self.download_iso_button = QPushButton("Download Windows ISO", self)
            self.download_iso_button.clicked.connect(download_windows_iso)
            layout.addWidget(self.download_iso_button)

            # Button to select ISO and list Windows versions
            self.select_iso_button = QPushButton("Select Windows ISO and List Versions", self)
            self.select_iso_button.clicked.connect(self.select_iso_file)
            layout.addWidget(self.select_iso_button)

            # Add dropdown to select the Windows version
            layout.addWidget(QLabel("Select Windows Version:"))
            layout.addWidget(self.version_selection)

            # Dropdown to select SD card/USB
            layout.addWidget(QLabel("Select Storage Device:"))
            layout.addWidget(self.device_selection)
            self.refresh_storage_devices()

            # Button to detect SD card/USB and create Windows boot media
            self.sd_card_button = QPushButton("Create Windows Boot Media on microSD/USB", self)
            self.sd_card_button.clicked.connect(self.create_storage_media)
            layout.addWidget(self.sd_card_button)

            # Button to switch to Windows
            self.switch_button = QPushButton("Switch to Windows", self)
            self.switch_button.clicked.connect(self.switch_to_windows)
            layout.addWidget(self.switch_button)

        elif self.os == "Windows":
            self.status_label.setText("Currently on Windows")
            layout.addWidget(self.status_label)

            # Button to switch back to SteamOS
            self.switch_button = QPushButton("Switch to SteamOS Game Mode", self)
            self.switch_button.clicked.connect(self.switch_to_steam_os)
            layout.addWidget(self.switch_button)

        self.setLayout(layout)

    def refresh_storage_devices(self):
        """
        Detect and list available storage devices (USB/microSD) for installation.
        """
        devices = detect_storage_device()
        if devices:
            self.device_selection.clear()
            self.device_selection.addItems(devices)
        else:
            QMessageBox.warning(self, "Error", "No storage devices detected. Please insert a USB or microSD card.")

    def select_iso_file(self):
        self.iso_file, _ = QFileDialog.getOpenFileName(self, "Select Windows ISO", "", "ISO Files (*.iso)")
        if self.iso_file:
            self.status_label.setText(f"Selected ISO: {self.iso_file}")
            windows_versions = list_windows_versions(self.iso_file)
            self.version_selection.clear()
            self.version_selection.addItems(windows_versions)
        else:
            self.status_label.setText("No ISO file selected.")

    def create_storage_media(self):
        storage_device = self.device_selection.currentText()
        selected_version = self.version_selection.currentText()
        if storage_device and self.iso_file:
            create_windows_media(storage_device, self.iso_file, selected_version)
        else:
            QMessageBox.warning(self, "Error", "Please select ISO file and storage device.")

    def switch_to_windows(self):
        """
        Switch from SteamOS to Windows.
        """
        os.system("sudo efibootmgr -n 1 && sudo reboot")  # Assuming Windows is boot entry 1

    def switch_to_steam_os(self):
        """
        Switch from Windows to SteamOS Game Mode.
        """
        os.system("bcdedit /set {bootmgr} bootsequence {your-efi-steamos-entry}")
        os.system("shutdown /r /t 0")  # Restart Windows

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DualBootApp()
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
