import anki
from anki.hooks import wrap
from datetime import datetime
from aqt import dialogs
from aqt import mw, addcards, editcurrent, browser
from aqt.qt import *
from aqt import mw
from aqt.qt import *
from aqt.utils import *
import json
import os
import pathlib
from pathlib import Path
import re
import zipfile
import time

addon_dir = Path(__file__).parents[0]
import sys
import json
import base64
from hashlib import sha256
import os
import platform
import subprocess
from aqt.utils import showInfo
from PyQt6.QtCore import PYQT_VERSION_STR
# Get the current PyQt version
pyqt_version_str = PYQT_VERSION_STR
anki_version = anki.version
first_dot_position = anki_version.find('.')
stripped_version = anki_version[0:first_dot_position]

config = mw.addonManager.getConfig(__name__)

def decrypt_data(encrypted_data, passphrase):
    hashed_passphrase = sha256(passphrase.encode()).hexdigest()
    decoded_data = base64.b64decode(encrypted_data).decode()
    return xor_encrypt_decrypt(decoded_data, hashed_passphrase)


def xor_encrypt_decrypt(data, key):
    from itertools import cycle

    return "".join(chr(ord(c) ^ ord(k)) for c, k in zip(data, cycle(key)))


def encrypt_data(data, passphrase):
    hashed_passphrase = sha256(passphrase.encode()).hexdigest()
    encrypted = xor_encrypt_decrypt(data, hashed_passphrase)
    return base64.b64encode(encrypted.encode()).decode()


addopenlink = False
adddownloadto = False
addpwd_inp = False


class DataWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.fields = []
        self.addon_name_input = None  # This will store the QLineEdit for the addon name
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)  # Hauptlayout für das gesamte Fenster

        # Layout für die Eingabefelder
        self.fields_layout = QVBoxLayout()

        # Füge das erste Eingabefeld-Paar hinzu
        self.addAddonName()

        self.deckoverviewlayout = QVBoxLayout()
        # Füge das erste Eingabefeld-Paar hinzu
        self.addInputFields()
        self.fields_layout.addLayout(self.deckoverviewlayout)
        # Inputfield-Button
        self.addInputFields_button = QPushButton("Add input field", self)
        self.addInputFields_button.clicked.connect(self.addInputFields)

        # Speichern-Button
        # self.save_button = QPushButton('Save Data', self)
        # self.save_button.clicked.connect(self.saveData)

        # Füge das Felder-Layout zum Hauptlayout hinzu
        main_layout.addLayout(self.fields_layout)

        self.checkbox_layout = QHBoxLayout()
        self.addPasswordProtect()
        self.addDownloadToLocationButton()
        self.addOpenLinkButton()
        self.fields_layout.addLayout(self.checkbox_layout)  # Add to the layout

        # Füge den Speichern-Button zum Hauptlayout hinzu
        main_layout.addWidget(self.addInputFields_button)
        # main_layout.addWidget(self.save_button)

        # Add a button to create the .ankiaddon file
        self.create_ankiaddon_button = QPushButton("Create .ankiaddon", self)
        self.create_ankiaddon_button.clicked.connect(self.createAnkiAddon)
        main_layout.addWidget(self.create_ankiaddon_button)

        # Fenstereigenschaften
        self.setGeometry(300, 300, 500, 200)
        self.setWindowTitle("Create a DeckLink Collection")

    def addInputFields(self):
        row_layout = QHBoxLayout()
        name_input = QLineEdit(self)
        name_input.setPlaceholderText("Write deck name here")
        link_input = QLineEdit(self)
        link_input.setPlaceholderText("Write link here (with http:// or https://)")
        row_layout.addWidget(name_input)
        row_layout.addWidget(link_input)
        self.fields.append((name_input, link_input))
        self.deckoverviewlayout.addLayout(row_layout)  # Füge dem Felder-Layout hinzu

    def format_drive_link(self, link):
        # Regex pattern to match the Google Drive file ID
        pattern = r"https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view"
        match = re.search(pattern, link)
        if match:
            file_id = match.group(1)  # Extracts the file ID from the URL
            direct_download_link = (
                f"https://drive.google.com/uc?export=download&id={file_id}"
            )
            return direct_download_link
        else:
            return link  # Return the original link if it's not a Google Drive link

    def createAnkiAddon(self):
        self.saveData()
        addon_name = (
            self.addon_name_input.text() if self.addon_name_input else "Default"
        )
        try:
            addon_files_dir = addon_dir / "addoncreatorfiles"
            addon_output_path = addon_dir / "output.ankiaddon"
            # Current date and time
            current_datetime = datetime.now()
            # Format date and time as DDMMYYYYTime
            formatted_datetime = current_datetime.strftime("%d%m%Y%H%M%S")
            # Create manifest.json
            manifest_data = {
                "package": f"{addon_name}",  # Replace with your folder name
                "name": f"DeckLink Collection: {addon_name}",  # Replace with your add-on's name
                "conflicts": [],
                "mod": int(time.time()),  # Sets to current Unix timestamp
                "version": f"{formatted_datetime}v",
                "min_anki_version": "2.1.36",
            }
            manifest_path = addon_files_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f, indent=4)

            data = {"update_enabled": True}
            # Create manifest.json
            meta_data = {
                "name": f"DeckLink Collection: {addon_name}",
                "mod": int(time.time()),
                "min_point_version": 1,
            }
            data.update(meta_data)
            meta_path = addon_files_dir / "meta.json"
            with open(meta_path, "w") as f:
                json.dump(data, f, indent=4)

            with zipfile.ZipFile(addon_output_path, "w") as zipf:
                for root, dirs, files in os.walk(addon_files_dir):
                    dirs[:] = [
                        d for d in dirs if d != "__pycache__"
                    ]  # Exclude __pycache__
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(
                            file_path, os.path.relpath(file_path, addon_files_dir)
                        )

                # Add the data.json file
                json_path = addon_dir / "encrypted_data.json"
                if json_path.exists():
                    zipf.write(json_path, "encrypted_data.json")
                else:
                    QMessageBox.warning(
                        self,
                        "Missing file",
                        "The data.json file does not exist and will not be included.",
                    )

            QMessageBox.information(
                self,
                "Success",
                f".ankiaddon file created at {addon_output_path}.<br>"
                "The next window will open a folder with 'output.ankiaddon'.<br><br>"
                "This is your addon file. Please copy it to a location of your choice and double-click it to install it in Anki.",
            )
            self.open_file_explorer(addon_dir)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def open_file_explorer(self, path):
        system_name = platform.system()

        if system_name == "Windows":
            # Open file explorer at the specified path in Windows
            subprocess.run(["explorer", path])
        elif system_name == "Darwin":
            # Open file explorer at the specified path in macOS
            subprocess.run(["open", path])
        elif system_name == "Linux":
            # Open file explorer at the specified path in Linux
            subprocess.run(["xdg-open", path])
        else:
            raise OSError(f"Unsupported operating system: {system_name}")

    def addAddonName(self):
        top_down_layout = QHBoxLayout()
        self.addon_name_input = QLineEdit(
            self
        )  # Use self to make it accessible elsewhere
        self.addon_name_input.setPlaceholderText("Write name for DeckLink Collection here")
        top_down_layout.addWidget(self.addon_name_input)
        self.fields_layout.addLayout(top_down_layout)  # Add to the layout

    def addPasswordProtect(self):
        # Create a check box
        checkbox = QCheckBox("Passwort protection", self)
        checkbox.stateChanged.connect(self.checkboxStateChanged)
        # self.addpwd_input = QLineEdit(self)  # Use self to make it accessible elsewhere
        # self.addpwd_input.setPlaceholderText(" = (Type 'True' or 'False' here)")
        self.checkbox_layout.addWidget(checkbox)

    def checkboxStateChanged(self, state):
        # self.addpwd_input = QLineEdit(self)  # Use self to make it accessible elsewhere
        # self.addpwd_input.setPlaceholderText("Type your Password here")
        global addpwd_inp
        if state == 2:
            # addpwd_inp == False:
            # self.addpwd_inp = True
            addpwd_inp = True
            showInfo("Password protection is activated.")
        # self.fields_layout.addWidget(self.addpwd_input)
        else:
            addpwd_inp = False
            showInfo("Password protection is deactivated.")

    def addDownloadToLocationButton(self):
        # Create a check box
        checkbox = QCheckBox("Download to Location Button", self)
        LocationButton = QHBoxLayout()
        checkbox.stateChanged.connect(self.checkboxStateChanged2)
        self.checkbox_layout.addWidget(checkbox)

    def checkboxStateChanged2(self, state):
        # checkbox für download to
        global adddownloadto
        if state == 2:
            adddownloadto = True
            showInfo(
                "\"Download to Location\" button will now be integrated into your addon!"
            )
        else:
            adddownloadto = False
            showInfo("\"Download to Location\" button is deactivated!")

    def addOpenLinkButton(self):
        # Create a check box
        checkbox = QCheckBox("OpenLink Button", self)
        LocationButton = QHBoxLayout()
        checkbox.stateChanged.connect(self.checkboxStateChanged3)
        self.checkbox_layout.addWidget(checkbox)

    def checkboxStateChanged3(self, state):
        global addopenlink
        if state == 2:
            addopenlink = True
            showInfo("\"Open Link\" button will now be integrated into your addon!")
        else:
            addopenlink = False
            showInfo("\"Open Link\" button is deactivated!")

    def saveData(self):
        global addon_dir, adddownloadto, addopenlink, addpwd_inp
        json_path = addon_dir / "encrypted_data.json"
        # Get the addon name and passphrase from the input fields
        addon_name = (
            self.addon_name_input.text() if self.addon_name_input else "Default"
        )
        config_path2 = addon_dir / "addoncreatorfiles" / "config2.json"
        config_data = [
            {
                "addopenlink": str(addopenlink),
                "adddownloadto": str(adddownloadto),
                "addpwd_inp": str(addpwd_inp),
                "DeckLinks name": str(addon_name),
            }
        ]
        with open(str(config_path2), "w", encoding="utf-8") as f:
            json.dump(config_data, f)
        if addpwd_inp is True:
            passphrase, ok = QInputDialog.getText(
                self, "Passphrase", "Enter passphrase for encryption:"
            )

            if not ok or not passphrase:
                QMessageBox.warning(
                    self,
                    "No passphrase",
                    "No passphrase provided. Aborting encryption.",
                )
                return

        all_data = {addon_name: []}
        for name_input, link_input in self.fields:
            name = name_input.text()
            link = self.format_drive_link(
                link_input.text()
            )  # Format link if it's a Google Drive link
            if name and link:
                all_data[addon_name].append({"name": name, "link": link})

        if addpwd_inp is True:
            # Encrypt the data before saving
            encrypted_data = encrypt_data(json.dumps(all_data), passphrase)

            # Format the encrypted data as a JSON array containing a single string
            data_json = json.dumps([encrypted_data])
        else:
            data_json = json.dumps([all_data])

        with open(str(json_path), "w", encoding="utf-8") as f:
            f.write(data_json)
        QMessageBox.information(
            self,
            "DeckLinks saved",
            f"Your encrypted decks and corresponding links were saved in the DeckLinks collection \"{addon_name}\"!",
        )


def openDataWindow():
    window = DataWindow()
    if int(stripped_version) == 23:
        window.exec()  # Jetzt funktioniert exec_(), da DataWindow von QDialog erbt
    else:
        window.exec_()


action = QAction("Create Deck Addon", mw)
action.triggered.connect(openDataWindow)
mw.form.menuTools.addAction(action)
