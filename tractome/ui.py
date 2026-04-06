import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ASSETS_PATH = Path(__file__).resolve().parent / "assets"
IMAGES_PATH = ASSETS_PATH / "images"


def load_style_sheet():
    """Load the stylesheet for the app.

    Returns
    -------
    str
        String value of the stylesheet.
    """
    style_path = Path(__file__).resolve().parent / "assets" / "style.qss"
    with style_path.open("r", encoding="utf-8") as f:
        return f.read()


def open_file_dialog(
    *, parent=None, title="Select a file", file_filter="All Files (*.*)"
):
    """Open a file dialog and return the selected file path.

    Parameters
    ----------
    title : str, optional
        Title of the file dialog, by default "Select a file"
    file_filter : str, optional
        Filter for the file types, by default "All Files (*.*)"

    Returns
    -------
    str
        Path to the selected file.
    """
    file_path, _ = QFileDialog.getOpenFileName(parent, title, "", file_filter)
    if file_path:
        logging.info(f"Selected file: {file_path}")
    else:
        logging.info("No file selected.")
    return file_path


class StartScreen(QWidget):
    """Start screen of the app."""

    def __init__(self, on_uploading_done):
        """Initialize the start screen."""
        super().__init__()

        self._on_uploading_done = on_uploading_done

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        self._container_box = QFrame()
        self._container_box.setObjectName("startScreenContainer")
        self._container_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        inner_layout = QVBoxLayout(self._container_box)
        inner_layout.setAlignment(Qt.AlignCenter)
        inner_layout.setSpacing(20)

        self._logo_label = QLabel()
        logo_pixmap = QPixmap(str(IMAGES_PATH / "logo.png"))
        scaled_logo = logo_pixmap.scaled(
            127, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self._logo_label.setPixmap(scaled_logo)
        self._logo_label.setAlignment(Qt.AlignCenter)

        inner_layout.addStretch()
        inner_layout.addWidget(self._logo_label)

        self._title_label = QLabel("T R A C T O M E")
        self._title_label.setObjectName("titleLabel")
        self._title_label.setAlignment(Qt.AlignCenter)

        inner_layout.addWidget(self._title_label)

        self._upload_button = QPushButton("UPLOAD TRACTOGRAM")
        self._upload_button.setObjectName("startUploadButton")
        self._upload_button.setFixedSize(260, 50)
        self._upload_button.setCursor(Qt.PointingHandCursor)
        self._upload_button.clicked.connect(self._on_upload_clicked)

        inner_layout.addSpacing(40)
        inner_layout.addWidget(self._upload_button, alignment=Qt.AlignCenter)
        inner_layout.addStretch()

        layout.addWidget(self._container_box)

    def _on_upload_clicked(self):
        """Handle the upload button click event."""
        file_path = open_file_dialog(
            title="Select a tractogram file",
            file_filter=(
                "Tractogram Files (*.trx *.trk);; TRX Files (*.trx);; "
                "TRK Files (*.trk);; All Files (*.*)"
            ),
        )
        if file_path:
            print(f"Selected file: {file_path}")
            self._on_uploading_done(file_path)


class InteractionScreen(QWidget):
    """Interaction screen of the app."""

    def __init__(self):
        """Initialize the interaction screen."""
        super().__init__()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        self._left_section = LeftSectionWidget()
        self._center_section = CenterSectionWidget()
        self._right_section = RightSectionWidget()

        main_layout.addWidget(self._left_section, 1)
        main_layout.addWidget(self._center_section, 3)
        main_layout.addWidget(self._right_section, 1)


class LeftSectionWidget(QFrame):
    """Left section container for interaction controls."""

    def __init__(self):
        super().__init__()
        self.setObjectName("interactionLeftSection")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addStretch()


class CenterSectionWidget(QFrame):
    """Center section container for visualization/content."""

    def __init__(self):
        super().__init__()
        self.setObjectName("interactionCenterSection")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addStretch()


class RightSectionWidget(QFrame):
    """Right section container for add-ons and track views."""

    def __init__(self):
        super().__init__()
        self.setObjectName("interactionRightSection")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addStretch()
