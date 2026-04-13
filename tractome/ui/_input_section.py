from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
)

from tractome.mem import input_manager, state_manager, visualization_manager
from tractome.ui._paths import ICONS_PATH
from tractome.ui.utils import open_file_dialog


class ImageInputWidget(QFrame):
    """Widget for displaying an image input."""

    t1_changed = Signal()
    t1_visibility_changed = Signal()
    t1_slices_changed = Signal(int, int, int)

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

        self.slice_controls_widget = QFrame(self)
        self.slice_controls_layout = QVBoxLayout(self.slice_controls_widget)
        self.slice_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.slice_controls_layout.setSpacing(0)

        self._slice_sliders = {}
        self._slice_labels = {}
        self._slice_checkboxes = {}
        for axis in ("x", "y", "z"):
            axis_layout = QVBoxLayout()
            axis_layout.setSpacing(4)
            axis_layout.setContentsMargins(8, 0, 8, 0)

            slice_label = QLabel("")
            slice_label.setObjectName("imageSliceLabel")
            axis_layout.addWidget(slice_label)

            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(0, 0, 0, 0)

            slice_slider = QSlider(Qt.Horizontal)
            slice_slider.setObjectName("imageSliceSlider")
            slice_slider.setRange(0, 0)
            slice_slider.setValue(0)
            row_layout.addWidget(slice_slider)

            slice_checkbox = QCheckBox()
            slice_checkbox.setObjectName("imageSliceCheckbox")
            slice_checkbox.setChecked(True)
            row_layout.addWidget(slice_checkbox)

            axis_layout.addLayout(row_layout)
            self.slice_controls_layout.addLayout(axis_layout)
            self._slice_labels[axis] = slice_label
            self._slice_sliders[axis] = slice_slider
            self._slice_checkboxes[axis] = slice_checkbox
        self.main_layout.addWidget(self.slice_controls_widget)

        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.t1_visibility_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.image_dropdown.currentIndexChanged.connect(self._on_selection_changed)
        self.t1_visibility_button.clicked.connect(self._on_t1_visibility_clicked)
        for axis in ("x", "y", "z"):
            self._slice_sliders[axis].valueChanged.connect(
                lambda _value, a=axis: self._on_slice_changed(a)
            )
            self._slice_checkboxes[axis].toggled.connect(
                lambda checked, a=axis: self._on_slice_toggled(a, checked)
            )

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refresh_images)
        self._poll_timer.start()

        self.refresh_images()
        self._sync_t1_visibility_appearance()
        self.sync_t1_slice_controls()

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
        self.slice_controls_widget.setVisible(has_t1)
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

    def configure_t1_slice_controls(self):
        """Update slice slider ranges from T1 bounding box and center state."""
        if not input_manager.has_t1:
            return

        t1_visualization = visualization_manager.t1_visualizations
        if not t1_visualization:
            return

        min_vals, max_vals = t1_visualization[0].get_bounding_box()
        axis_bounds = [
            (int(min_vals[0]), int(max_vals[0])),
            (int(min_vals[1]), int(max_vals[1])),
            (int(min_vals[2]), int(max_vals[2])),
        ]
        midpoint_state = []
        for axis, (min_value, max_value) in zip(("x", "y", "z"), axis_bounds):
            slider = self._slice_sliders[axis]
            slider.blockSignals(True)
            slider.setRange(min_value, max_value)
            midpoint = int((min_value + max_value) / 2)
            slider.setValue(midpoint)
            slider.blockSignals(False)
            midpoint_state.append(midpoint)

        state_manager.t1_state = midpoint_state
        self.sync_t1_slice_controls()

    def sync_t1_slice_controls(self):
        """Sync labels and values from state_manager.t1_state."""
        for index, axis in enumerate(("x", "y", "z")):
            slider = self._slice_sliders[axis]
            checkbox = self._slice_checkboxes[axis]
            slider.blockSignals(True)
            value = min(
                max(int(state_manager.t1_state[index]), slider.minimum()),
                slider.maximum(),
            )
            slider.setValue(value)
            slider.blockSignals(False)
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(state_manager.t1_slice_visibility[index]))
            checkbox.blockSignals(False)
            self._slice_labels[axis].setText(f"{axis.upper()} slice: {value}")
            slider.setEnabled(checkbox.isChecked())

    def emit_current_slices(self):
        """Emit the current XYZ slice tuple."""
        self.t1_slices_changed.emit(
            self._slice_sliders["x"].value(),
            self._slice_sliders["y"].value(),
            self._slice_sliders["z"].value(),
        )

    def _on_slice_changed(self, axis):
        """Update axis label/state and propagate current slice tuple."""
        axis_index = {"x": 0, "y": 1, "z": 2}[axis]
        value = self._slice_sliders[axis].value()
        self._slice_labels[axis].setText(f"{axis.upper()} slice: {value}")
        state_manager.t1_state[axis_index] = value
        self.emit_current_slices()

    def _on_slice_toggled(self, axis, checked):
        """Enable axis slider and update per-slice visibility."""
        self._slice_sliders[axis].setEnabled(checked)
        state_manager.t1_slice_visibility = [
            self._slice_checkboxes[current_axis].isChecked()
            for current_axis in ("x", "y", "z")
        ]
        visualization_manager.toggle_t1_slice_visibility(
            *state_manager.t1_slice_visibility
        )
        self.t1_visibility_changed.emit()

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
