from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from tractome.mem import input_manager, visualization_manager
from tractome.ui._paths import ICONS_PATH
from tractome.ui.utils import open_file_dialog


class ImageInputWidget(QFrame):
    """Widget for displaying an image input."""

    t1_changed = Signal()
    t1_visibility_changed = Signal()

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("imageInputWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        self.title = QLabel("IMAGE")
        self.title.setObjectName("imageTitle")
        self.main_layout.addWidget(self.title)

        self.file_input_layout = QHBoxLayout()
        self.file_input_layout.setSpacing(8)
        self.file_input_layout.setContentsMargins(8, 8, 8, 8)

        std_h = 38

        self.upload_button = QPushButton("")
        self.upload_button.setIcon(QIcon(str(ICONS_PATH / "upload.svg")))
        self.upload_button.setIconSize(QSize(16, 16))
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.setFixedSize(std_h, std_h)
        self.file_input_layout.addWidget(self.upload_button)

        self.image_dropdown = QComboBox()
        self.image_dropdown.setObjectName("imageInputDropdown")
        self.image_dropdown.setFixedHeight(std_h)
        self.image_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_input_layout.addWidget(self.image_dropdown)

        self.t1_visibility_button = QPushButton("")
        self.t1_visibility_button.setObjectName("t1VisibilityButton")
        self.t1_visibility_button.setIcon(QIcon(str(ICONS_PATH / "eye.svg")))
        self.t1_visibility_button.setIconSize(QSize(18, 18))
        self.t1_visibility_button.setFixedSize(std_h, std_h)
        self.t1_visibility_effect = QGraphicsOpacityEffect(self.t1_visibility_button)
        self.t1_visibility_button.setGraphicsEffect(self.t1_visibility_effect)
        self.file_input_layout.addWidget(self.t1_visibility_button)

        self.main_layout.addLayout(self.file_input_layout)

        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.t1_visibility_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.image_dropdown.currentIndexChanged.connect(self._on_selection_changed)
        self.t1_visibility_button.clicked.connect(self._on_t1_visibility_clicked)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refresh_images)
        self._poll_timer.start()

        self.refresh_images()
        self._sync_t1_visibility_appearance()

    def _scroll_dropdown_text_to_start(self):
        """Long filenames scroll horizontally; keep the start (basename) visible."""
        le = self.image_dropdown.lineEdit()
        if le is None:
            return
        le.setCursorPosition(0)
        le.deselect()

    def _schedule_dropdown_text_to_start(self):
        """After layout/index updates, scroll so the start of the name is visible."""
        QTimer.singleShot(0, self._scroll_dropdown_text_to_start)

    def _on_t1_visibility_clicked(self):
        """Toggle T1 scene visibility and dim the eye icon when hidden."""
        visualization_manager.toggle_t1_visibility()
        self._sync_t1_visibility_appearance()
        self.t1_visibility_changed.emit()

    def sync_t1_visibility_button(self):
        """Update eye icon opacity from the current T1 visibility in the scene."""
        self._sync_t1_visibility_appearance()

    def _sync_t1_visibility_appearance(self):
        """White (full opacity) when visible, lighter when hidden."""
        has_t1 = input_manager.has_t1
        self.t1_visibility_button.setVisible(has_t1)
        if not has_t1:
            return
        if visualization_manager.t1_is_visible:
            self.t1_visibility_effect.setOpacity(1.0)
        else:
            self.t1_visibility_effect.setOpacity(0.42)

    def _on_upload_clicked(self):
        """Upload a T1 image and set it as current."""
        file_path = open_file_dialog(
            parent=self,
            title="Select a T1 image",
            file_filter=(
                "NIfTI Files (*.nii *.nii.gz);; NII Files (*.nii);; "
                "NII.GZ Files (*.nii.gz);; All Files (*.*)"
            ),
        )
        if not file_path:
            return

        input_manager.add_t1(file_path)
        self.refresh_images()
        self.t1_changed.emit()

    def _on_selection_changed(self, index):
        """Switch current image to the selected dropdown entry."""
        if index < 0:
            return

        path = self.image_dropdown.itemData(index, Qt.UserRole)
        if not path:
            return

        input_manager.add_t1(path)
        self.refresh_images()
        self.t1_changed.emit()

    def refresh_images(self):
        """Synchronize the dropdown with available and current images."""
        options = list(input_manager.provided_images)

        try:
            _, _, current_path, _ = input_manager.get_current_t1()
        except ValueError:
            current_path = None

        current_items = [
            self.image_dropdown.itemData(i, Qt.UserRole)
            for i in range(self.image_dropdown.count())
        ]
        if current_items == options:
            self._set_current_path(current_path)
        else:
            self.image_dropdown.blockSignals(True)
            self.image_dropdown.clear()
            for path in options:
                self.image_dropdown.addItem(Path(path).name, path)
            self._set_current_path(current_path)
            self.image_dropdown.blockSignals(False)
        self._sync_t1_visibility_appearance()

    def _set_current_path(self, current_path):
        """Apply current T1 path in the combo selection."""
        self.image_dropdown.blockSignals(True)
        try:
            if not current_path:
                self.image_dropdown.setCurrentIndex(-1)
            else:
                idx = self.image_dropdown.findData(current_path, Qt.UserRole)
                self.image_dropdown.setCurrentIndex(idx)
        finally:
            self.image_dropdown.blockSignals(False)
        self._schedule_dropdown_text_to_start()


class RightSectionWidget(QFrame):
    """Right section container for add-ons and track views."""

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("interactionRightSection")
        self.setFrameShape(QFrame.StyledPanel)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)
        self.main_layout.addStretch()

        self.image_input_widget = ImageInputWidget(parent=self)
        self.main_layout.addWidget(self.image_input_widget)

        self.main_layout.addStretch()
