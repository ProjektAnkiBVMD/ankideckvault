# -*- coding: utf-8 -*-
import os
import anki
import json
import tempfile
import webbrowser
import requests
import time
import zipfile
from aqt import mw
from aqt.qt import *
from aqt.utils import showWarning, showInfo
from anki.importing.apkg import AnkiPackageImporter
from pathlib import Path
from tempfile import NamedTemporaryFile
import base64
from hashlib import sha256
from bs4 import BeautifulSoup
from aqt.utils import showInfo
from PyQt6.QtCore import PYQT_VERSION_STR

# Get the current PyQt version
pyqt_version_str = PYQT_VERSION_STR
anki_version = anki.version
first_dot_position = anki_version.find('.')
stripped_version = anki_version[0:first_dot_position]

# Ensure that your addon directory is correctly referenced
addon_dir = Path(__file__).parent
# Define the file path to your JSON file
config_path = addon_dir / "config2.json"  # Replace with the actual file path

# Get the current PyQt version
pyqt_version_str = PYQT_VERSION_STR
anki_version = anki.version
first_dot_position = anki_version.find('.')
stripped_version = anki_version[0:first_dot_position]

# Initialize default values for the variables
addopenlink = "False"
adddownloadto = "False"
addpwd_inp = "False"
DeckLinks_name = "Deck"
try:
    with open(config_path, "r") as file:
        data = json.load(file)

    # Check if the data is a list with at least one item
    if isinstance(data, list) and len(data) > 0:
        config_data = data[0]

        # Update the variables based on the data from the JSON file
        if "addopenlink" in config_data:
            addopenlink = config_data["addopenlink"]

        if "adddownloadto" in config_data:
            adddownloadto = config_data["adddownloadto"]

        if "addpwd_inp" in config_data:
            addpwd_inp = config_data["addpwd_inp"]

        if "DeckLinks name" in config_data:
            DeckLinks_name = config_data["DeckLinks name"]

except FileNotFoundError:
    showWarning(f"File not found: {config_path}. The config file is missing!")
except json.JSONDecodeError:
    showWarning(f"Invalid JSON format in file: {config_path}")


# showInfo(f"{adddownloadto} , {addpwd_inp}, {addopenlink}")


def xor_encrypt_decrypt(data, key):
    from itertools import cycle

    return "".join(chr(ord(c) ^ ord(k)) for c, k in zip(data, cycle(key)))


def encrypt_data(data, passphrase):
    hashed_passphrase = sha256(passphrase.encode()).hexdigest()
    encrypted = xor_encrypt_decrypt(data, hashed_passphrase)
    return base64.b64encode(encrypted.encode()).decode()


def decrypt_data(encrypted_data, passphrase):
    hashed_passphrase = sha256(passphrase.encode()).hexdigest()
    decoded_data = base64.b64decode(encrypted_data).decode()
    return xor_encrypt_decrypt(decoded_data, hashed_passphrase)


class LinkViewer(QDialog):
    def __init__(self, data, parent=mw):
        super().__init__(parent)
        # data = load_data()
        self.setGeometry(300, 300, 500, 200)
        self.data = data
        self.temp_files = []  # List to keep track of temporary file paths
        self.initUI()

    def initUI(self):
        global addopenlink, adddownloadto, addpwd_inp
        main_layout = QVBoxLayout(self)
        collection_name, entries = next(iter(self.data.items()))
        self.setWindowTitle(f"Deck Links - {collection_name}")

        # Create and add a label for the collection name below the passphrase input
        collection_label = QLabel(f"{collection_name}")
        if int(stripped_version) == 23:
            collection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            collection_label.setAlignment(Qt.AlignCenter)
        font = collection_label.font()
        font.setPointSize(14)
        collection_label.setFont(font)
        main_layout.addWidget(collection_label)

        # Apply a stylesheet to the label for a nice style
        collection_label.setStyleSheet(
            """
            QLabel {
                color: white;
                background-color: #6D6D6D;
                padding: 5px;
                border-radius: 5px;
            }
        """
        )

        # Create the scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Container widget for the scroll area
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        # Apply the same style to the container widget
        container_widget.setStyleSheet(
            """
            QWidget {
                background-color: #1C1C1C;  #  gray background for the container
                border: 1px solid #DDD;  # Add a subtle border
            }
        """
        )

        # Layout for the container widget
        container_layout = QVBoxLayout(container_widget)

        for entry in entries:
            name = entry.get("name", "No Name")
            link = entry.get("link", None)

            if not link or link == "#":
                showWarning(f"The link for '{name}' is missing or invalid.")
                continue  # Skip this entry

            # Create a frame for each entry to apply the border
            entry_frame = QFrame()

            if int(stripped_version) == 23:
                entry_frame.setFrameShape(QFrame.Shape.StyledPanel)
            else:
                entry_frame.setFrameShape(QFrame.StyledPanel)  # Styled panel frame shape

            entry_frame.setStyleSheet(
                """
                            QFrame {
                                padding: 5px;  # Space inside the frame
                                margin: auto;  # Space outside the frame
                                border: 1px solid #007ACC;  # Blue border
                                border-radius: 5px;  # Rounded corners
                            }
                        """
            )

            if link == "Subtitle":
                hlayout = QHBoxLayout(entry_frame)  # Set the frame as the parent of hlayout
                label = QLabel(name)
                # Set the font size using QFont
                font = QFont()
                font.setPointSize(25)  # Set the font size to 16
                label.setFont(font)
            elif link == "Info":
                hlayout = QHBoxLayout(entry_frame)  # Set the frame as the parent of hlayout
                label = QLabel(name)
                if int(stripped_version) == 23:
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    label.setAlignment(Qt.AlignCenter)
                font = QFont()
                font.setPointSize(16)  # Set the font size to 16
                label.setFont(font)
            else:
                hlayout = QHBoxLayout(entry_frame)  # Set the frame as the parent of hlayout
                label = QLabel(name)
            hlayout.addWidget(label)

            if link != "Subtitle" and link != "Info":
                if addopenlink == "True":
                    open_button = QPushButton("Open Link", self)
                    open_button.clicked.connect(lambda _, link=link: self.openLink(link))
                    hlayout.addWidget(open_button)

                import_button = QPushButton("Download and Import", self)
                import_button.clicked.connect(
                    lambda _, link=link: self.downloadAndImportDeck(link)
                )
                hlayout.addWidget(import_button)

                if adddownloadto == "True":
                    import_button_to = QPushButton("Download to Location and Import", self)
                    import_button_to.clicked.connect(
                        lambda _, link=link: self.downloadAndImportDeckwithdownloadto(link)
                    )
                    hlayout.addWidget(import_button_to)

            container_layout.addLayout(hlayout)
            container_layout.addWidget(
                entry_frame
            )  # Add the frame to the container layout

    def openLink(self, link):
        webbrowser.open(link)

    def downloadAndImportDeck(self, link):
        try:
            deck_path = addon_dir / "downloaded_deck.apkg"
            if link.startswith("https://drive.usercontent.google.com/download"):
                # Set the path for the downloaded deck
                # Specify the URL you want to fetch the HTML content from
                url = f"{link}"  # Replace with your actual URL

                def get_html_content(link):
                    # Send a GET request to the specified URL
                    try:
                        response = requests.get(link)

                        # Check if the request was successful
                        if response.status_code == 200:
                            # Save the HTML content of the page in the html_content variable
                            html_content = response.text
                        else:
                            showWarning(
                                f"Failed to retrieve the HTML content. Status code: {response.status_code}"
                            )
                            html_content = ""

                        return f"{html_content}"
                    except Exception as e:
                        showWarning(f"An error occured {e}")

                html_content = get_html_content(url)

                def get_info(html_content):
                    # Parse the HTML content with BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Find the form by its ID
                    form = soup.find("form", {"id": "download-form"})
                    # Initialize a dictionary to hold the extracted values
                    form_data = {}

                    # Check if the form is found
                    if form:
                        # Extract the values of 'id', 'authuser', 'export', and 'confirm' inputs
                        form_data["id"] = form.find("input", {"name": "id"})["value"]
                        form_data["authuser"] = form.find(
                            "input", {"name": "authuser"}
                        )["value"]
                        form_data["export"] = form.find("input", {"name": "export"})[
                            "value"
                        ]
                        form_data["confirm"] = form.find("input", {"name": "confirm"})[
                            "value"
                        ]
                    else:
                        showWarning(f"{form} is empty !")
                    return form_data

                form_data = get_info(html_content)

                # showInfo("get info succesful")
                def download_file(form_data, url, destination):
                    try:
                        # These are the form fields extracted from the HTML form
                        params = {
                            "id": form_data["id"],
                            "export": form_data["export"],
                            "authuser": form_data["authuser"],
                            "confirm": form_data["confirm"],
                            # The value for the 'confirm' might change and needs to be extracted dynamically
                        }

                        # The action URL from the form
                        action_url = "https://drive.usercontent.google.com/download"

                        # Submit the form by sending a GET request with the parameters
                        with requests.get(
                                action_url, params=params, stream=True
                        ) as response:
                            response.raise_for_status()  # Check for HTTP errors
                            total_length = int(response.headers.get("content-length", 0))

                            # Initialize the progress dialog
                            dlg = QProgressDialog("Downloading deck...", "Abort", 0, total_length, self)
                            dlg.setWindowTitle("Download progress")
                            # if int(stripped_version) == 23:
                            # dlg.setWindowModality(Qt.WindowType.WindowModal)
                            # else:
                            # dlg.setWindowModality(Qt.WindowModal)
                            dlg.setModal(True)  # Set the dialog as modal
                            dlg.setAutoReset(False)
                            dlg.show()
                            # Write to the file in chunks and update the progress bar
                            with open(deck_path, "wb") as f:
                                downloaded = 0
                                for chunk in response.iter_content(chunk_size=16384):
                                    if chunk:  # filter out keep-alive new chunks
                                        downloaded += len(chunk)
                                        f.write(chunk)
                                        dlg.setValue(downloaded)
                                        QApplication.processEvents()  # Process UI events to update the dialog
                                        if dlg.wasCanceled():
                                            f.close()  # Close the file
                                            os.remove(deck_path)  # Delete the partial file
                                            return  # Exit the function

                        showInfo("File has been downloaded! Starting to import now!")
                        # Import the deck to Anki
                        try:
                            mw.taskman.run_on_main(lambda: self.importDeck(deck_path))
                        except Exception as e:
                            showWarning(f"An error occured when importing: {e}")
                    except Exception as e:
                        showWarning(f"An error occured when downloading: {e}")

                download_file(form_data, link, deck_path)
            else:
                # Create a session object for persistent connections
                with requests.Session() as session:
                    with session.get(link, stream=True) as response:
                        response.raise_for_status()  # Check for HTTP errors
                        total_length = int(response.headers.get("content-length", 0))

                        # Initialize the progress dialog
                        dlg = QProgressDialog(
                            "Downloading deck...", "Abort", 0, total_length, self
                        )
                        dlg.setWindowTitle("Download progress")
                        if int(stripped_version) == 23:
                            dlg.setWindowModality(Qt.WindowType.WindowModal)
                        else:
                            dlg.setWindowModality(Qt.WindowModal)
                        dlg.setAutoReset(False)
                        dlg.show()

                        # Write to the file in chunks and update the progress bar
                        with open(deck_path, "wb") as f:
                            downloaded = 0
                            for chunk in response.iter_content(chunk_size=4096):
                                if chunk:  # filter out keep-alive new chunks
                                    downloaded += len(chunk)
                                    f.write(chunk)
                                    dlg.setValue(downloaded)
                                    QApplication.processEvents()  # Process UI events to update the dialog
                                    if dlg.wasCanceled():
                                        f.close()  # Close the file
                                        os.remove(deck_path)  # Delete the partial file
                                        return  # Exit the function
                try:
                    showInfo("File has been downloaded! Starting to import now!")
                    mw.taskman.run_on_main(lambda: self.importDeck(deck_path))
                except Exception as e:
                    showWarning(f"An error occured when importing: {e}")
        except Exception as e:
            showWarning(f"An error occured when downloading: {e}")

    def importDeck(self, deck_path):
        try:
            importer = AnkiPackageImporter(mw.col, str(deck_path))
            importer.run()
            showInfo(
                "Deck imported successfully! \n Please refresh your Deck Overview by clicking on 'Decks'"
            )
        except Exception as e:
            showWarning(f"Failed to import the deck: {e}")

    def downloadAndImportDeckwithdownloadto(self, link):
        try:
            # Ask user where to save the downloaded file
            deck_path, _ = QFileDialog.getSaveFileName(
                self, "Save Deck", "", "Anki Deck (*.apkg)"
            )
            if not deck_path:
                # User cancelled the save dialog
                return

            # Create a session object for persistent connections
            with requests.Session() as session:
                with session.get(link, stream=True) as response:
                    response.raise_for_status()  # Check for HTTP errors

                    # Open the file with the chosen path and write to it
                    with open(deck_path, "wb") as f:
                        for chunk in response.iter_content(
                                chunk_size=1024 * 1024
                        ):  # 1 MB chunks
                            if chunk:  # filter out keep-alive new chunks
                                f.write(chunk)

            # Check if the file is a valid zip file
            if zipfile.is_zipfile(deck_path):
                # Import the deck to Anki
                importer = AnkiPackageImporter(mw.col, deck_path)
                importer.run()
                showInfo("Deck imported successfully!")
            else:
                raise Exception("The downloaded file is not a valid zip file.")

        except Exception as e:
            showWarning(f"Failed to import the deck: {e}")

    # New method to override the close event
    def closeEvent(self, event):
        super().closeEvent(event)
        for file_path in self.temp_files:
            try:
                os.remove(file_path)
            except Exception as e:
                showWarning(f"Could not delete the temporary file: {e}")


def load_data():
    global addon_dir, addpwd_inp
    json_path = addon_dir / "encrypted_data.json"
    # try:
    with open(str(json_path), "r", encoding="utf-8") as f:
        encrypt_data = json.load(f)
        encrypt_data = encrypt_data[0]
        if addpwd_inp == "True":
            passphrase, ok_pressed = QInputDialog.getText(
                None, "Passphrase", "Enter passphrase for encryption:"
            )
            if passphrase:
                json_string = decrypt_data(encrypt_data, f"{passphrase}")
                try:
                    data = json.loads(json_string)
                    return data
                except:
                    showWarning("Passphrase incorrect or file corrupt!")
                    return None
            else:
                showWarning(
                    "Please repeat the process but remember to input a passphrase."
                )
        else:
            try:
                return encrypt_data
            except Exception as e:
                showWarning(f"An error occured: {e}!")
                return None


def openLinkViewer():
    data = load_data()
    if data:
        try:
            viewer = LinkViewer(data)
            if int(stripped_version) == 23:
                viewer.exec()  # Jetzt funktioniert exec_(), da DataWindow von QDialog erbt
            else:
                viewer.exec_()
        except Exception as e:
            showWarning(f"Error opening LinkViewer: {e}")


action = QAction(f"View {DeckLinks_name} Links", mw)
action.triggered.connect(openLinkViewer)
mw.form.menuTools.addAction(action)
