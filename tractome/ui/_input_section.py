from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
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
        self._slice_radios = {}
        self._slice_rows = {}
        self._slice_control_mode = "checkbox"
        self._slice_radio_group = QButtonGroup(self)
        self._slice_radio_group.setExclusive(True)
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

            slice_radio = QRadioButton()
            slice_radio.setObjectName("imageSliceRadio")
            slice_radio.setVisible(False)
            self._slice_radio_group.addButton(slice_radio)
            row_layout.addWidget(slice_radio)

            axis_layout.addLayout(row_layout)
            self.slice_controls_layout.addLayout(axis_layout)
            self._slice_labels[axis] = slice_label
            self._slice_sliders[axis] = slice_slider
            self._slice_checkboxes[axis] = slice_checkbox
            self._slice_radios[axis] = slice_radio
            self._slice_rows[axis] = row_layout
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
            self._slice_radios[axis].toggled.connect(
                lambda checked, a=axis: self._on_slice_radio_toggled(a, checked)
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
        """White (full opacity) when visible, lighter when hidden.

        The eye toggle is also hidden when slice controls are in radio
        mode (2D view), where the active slice is always shown.
        """
        has_t1 = input_manager.has_t1
        is_radio = self._slice_control_mode == "radio"
        self.t1_visibility_button.setVisible(has_t1 and not is_radio)
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
        is_radio = self._slice_control_mode == "radio"
        if is_radio:
            visibility = state_manager.t1_slice_visibility_2d
        else:
            visibility = state_manager.t1_slice_visibility
        for index, axis in enumerate(("x", "y", "z")):
            slider = self._slice_sliders[axis]
            checkbox = self._slice_checkboxes[axis]
            radio = self._slice_radios[axis]
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
            radio.blockSignals(True)
            radio.setChecked(bool(visibility[index]) if is_radio else False)
            radio.blockSignals(False)
            self._slice_labels[axis].setText(f"{axis.upper()} slice: {value}")
            slider.setEnabled(bool(visibility[index]))

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
        """Enable axis slider and update per-slice visibility (3D mode)."""
        if self._slice_control_mode != "checkbox":
            return
        self._slice_sliders[axis].setEnabled(checked)
        state_manager.t1_slice_visibility = [
            self._slice_checkboxes[current_axis].isChecked()
            for current_axis in ("x", "y", "z")
        ]
        visualization_manager.toggle_t1_slice_visibility(
            *state_manager.t1_slice_visibility
        )
        self.t1_visibility_changed.emit()

    def _on_slice_radio_toggled(self, axis, checked):
        """Show only the selected axis on the 2D scene (radio mode)."""
        if self._slice_control_mode != "radio" or not checked:
            return
        for current_axis in ("x", "y", "z"):
            self._slice_sliders[current_axis].setEnabled(current_axis == axis)
        state_manager.t1_slice_visibility_2d = [
            self._slice_radios[current_axis].isChecked()
            for current_axis in ("x", "y", "z")
        ]
        visualization_manager.toggle_t1_slice_visibility_2d(
            *state_manager.t1_slice_visibility_2d
        )
        self.t1_visibility_changed.emit()

    def set_slice_control_mode(self, mode):
        """Swap the per-axis selector between checkbox and radio variants.

        In radio mode the global T1 visibility eye is hidden as well: 2D
        mode always renders the selected slice, so the toggle is moot.

        Parameters
        ----------
        mode : str
            ``"checkbox"`` for 3D mode (independent toggles) or ``"radio"``
            for 2D mode (single visible axis).
        """
        if mode not in ("checkbox", "radio"):
            raise ValueError(f"Unknown slice control mode: {mode}")
        self._slice_control_mode = mode
        is_radio = mode == "radio"
        for axis in ("x", "y", "z"):
            self._slice_checkboxes[axis].setVisible(not is_radio)
            self._slice_radios[axis].setVisible(is_radio)
        self._sync_t1_visibility_appearance()
        self.sync_t1_slice_controls()

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


class MeshInputWidget(QFrame):
    """Widget for mesh (.obj) and texture (.jpg / .png) inputs."""

    mesh_changed = Signal()
    mesh_visibility_changed = Signal()
    mesh_material_changed = Signal()
    mesh_opacity_changed = Signal(int)

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("meshInputWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        self.title = QLabel("MESH")
        self.title.setObjectName("meshTitle")
        self.main_layout.addWidget(self.title)

        std_h = 38

        self.mesh_row = QHBoxLayout()
        self.mesh_row.setSpacing(8)
        self.mesh_row.setContentsMargins(8, 0, 8, 0)

        self.mesh_upload_button = QPushButton("")
        self.mesh_upload_button.setIcon(QIcon(str(ICONS_PATH / "upload.svg")))
        self.mesh_upload_button.setIconSize(QSize(16, 16))
        self.mesh_upload_button.setObjectName("uploadButton")
        self.mesh_upload_button.setFixedSize(std_h, std_h)
        self.mesh_upload_button.setToolTip(
            "Select mesh (.obj), then texture image (.jpg / .png)"
        )
        self.mesh_row.addWidget(self.mesh_upload_button)

        self.mesh_dropdown = QComboBox()
        self.mesh_dropdown.setObjectName("meshInputDropdown")
        self.mesh_dropdown.setFixedHeight(std_h)
        self.mesh_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mesh_dropdown.setEditable(True)
        self.mesh_row.addWidget(self.mesh_dropdown)
        _mle = self.mesh_dropdown.lineEdit()
        if _mle is not None:
            _mle.setObjectName("meshInputDropdownLineEdit")

        self.mesh_visibility_button = QPushButton("")
        self.mesh_visibility_button.setObjectName("meshVisibilityButton")
        self.mesh_visibility_button.setIcon(QIcon(str(ICONS_PATH / "eye.svg")))
        self.mesh_visibility_button.setIconSize(QSize(18, 18))
        self.mesh_visibility_button.setFixedSize(std_h, std_h)
        self.mesh_visibility_effect = QGraphicsOpacityEffect(
            self.mesh_visibility_button
        )
        self.mesh_visibility_button.setGraphicsEffect(self.mesh_visibility_effect)
        self.mesh_row.addWidget(self.mesh_visibility_button)

        self.mesh_remove_button = QPushButton("×")
        self.mesh_remove_button.setObjectName("meshRemoveButton")
        self.mesh_remove_button.setFixedSize(std_h, std_h)
        self.mesh_row.addWidget(self.mesh_remove_button)

        self.main_layout.addLayout(self.mesh_row)

        self._mesh_controls = QWidget()
        self._mesh_controls.setObjectName("meshExtraControls")
        mesh_controls_layout = QVBoxLayout(self._mesh_controls)
        mesh_controls_layout.setContentsMargins(0, 0, 0, 0)
        mesh_controls_layout.setSpacing(8)

        opacity_header = QHBoxLayout()
        self.opacity_label = QLabel("Opacity")
        self.opacity_label.setObjectName("meshOpacityLabel")
        opacity_header.addWidget(self.opacity_label)
        opacity_header.addStretch()
        mesh_controls_layout.addLayout(opacity_header)

        opacity_slider_row = QHBoxLayout()
        self.opacity_min_label = QLabel("0")
        self.opacity_min_label.setObjectName("meshOpacityTickLabel")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setObjectName("meshOpacitySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_max_label = QLabel("100")
        self.opacity_max_label.setObjectName("meshOpacityTickLabel")
        opacity_slider_row.addWidget(self.opacity_min_label)
        opacity_slider_row.addWidget(self.opacity_slider)
        opacity_slider_row.addWidget(self.opacity_max_label)
        mesh_controls_layout.addLayout(opacity_slider_row)

        self.material_row = QHBoxLayout()
        self.material_row.setSpacing(16)
        self.material_row.setContentsMargins(8, 0, 8, 0)
        self.photographic_checkbox = QCheckBox("Photographic")
        self.photographic_checkbox.setObjectName("meshMaterialCheckbox")
        self.project_checkbox = QCheckBox("Project")
        self.project_checkbox.setObjectName("meshMaterialCheckbox")
        self.material_row.addWidget(self.photographic_checkbox)
        self.material_row.addWidget(self.project_checkbox)
        self.material_row.addStretch()
        mesh_controls_layout.addLayout(self.material_row)

        self.main_layout.addWidget(self._mesh_controls)

        self.mesh_upload_button.setCursor(Qt.PointingHandCursor)
        self.mesh_visibility_button.setCursor(Qt.PointingHandCursor)
        self.mesh_remove_button.setCursor(Qt.PointingHandCursor)

        self.mesh_upload_button.clicked.connect(self._on_mesh_upload_clicked)
        self.mesh_dropdown.currentIndexChanged.connect(self._on_mesh_dropdown_changed)
        self.mesh_visibility_button.clicked.connect(self._on_mesh_visibility_clicked)
        self.mesh_remove_button.clicked.connect(self._on_remove_mesh_clicked)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.photographic_checkbox.toggled.connect(self._on_photographic_toggled)
        self.project_checkbox.toggled.connect(self._on_project_toggled)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refresh_mesh_lists)
        self._poll_timer.start()

        self.refresh_mesh_lists()
        self._sync_mesh_visibility_appearance()
        self._sync_material_checkboxes_from_state()

    def _scroll_mesh_dropdown_to_start(self):
        le = self.mesh_dropdown.lineEdit()
        if le is not None:
            le.setCursorPosition(0)
            le.deselect()

    def _schedule_mesh_dropdown_scroll(self):
        QTimer.singleShot(0, self._scroll_mesh_dropdown_to_start)

    def _on_mesh_visibility_clicked(self):
        visualization_manager.toggle_mesh_visibility()
        self._sync_mesh_visibility_appearance()
        self.mesh_visibility_changed.emit()

    def _sync_mesh_visibility_appearance(self):
        has_mesh = input_manager.has_mesh
        self.mesh_visibility_button.setVisible(has_mesh)
        self.mesh_remove_button.setEnabled(has_mesh)
        self._update_mesh_controls_visibility()
        if not has_mesh:
            return
        if visualization_manager.mesh_is_visible:
            self.mesh_visibility_effect.setOpacity(1.0)
        else:
            self.mesh_visibility_effect.setOpacity(0.42)

    def _update_mesh_controls_visibility(self):
        self._mesh_controls.setVisible(input_manager.has_mesh)

    def _apply_mesh_mode_from_checkboxes(self):
        if self.photographic_checkbox.isChecked():
            state_manager.mesh_mode = "photographic"
        elif self.project_checkbox.isChecked():
            state_manager.mesh_mode = "project"
        else:
            state_manager.mesh_mode = "photographic"

    def _sync_material_checkboxes_from_state(self):
        self.photographic_checkbox.blockSignals(True)
        self.project_checkbox.blockSignals(True)
        mode = state_manager.mesh_mode
        if mode == "photographic":
            self.photographic_checkbox.setChecked(True)
            self.project_checkbox.setChecked(False)
        elif mode == "project":
            self.photographic_checkbox.setChecked(False)
            self.project_checkbox.setChecked(True)
        else:
            # Legacy "normals" was the Project / phong path before mode rename
            self.photographic_checkbox.setChecked(False)
            self.project_checkbox.setChecked(True)
        self.photographic_checkbox.blockSignals(False)
        self.project_checkbox.blockSignals(False)

    def _on_photographic_toggled(self, checked):
        if checked:
            self.project_checkbox.blockSignals(True)
            self.project_checkbox.setChecked(False)
            self.project_checkbox.blockSignals(False)
        elif not self.project_checkbox.isChecked():
            self.project_checkbox.blockSignals(True)
            self.project_checkbox.setChecked(True)
            self.project_checkbox.blockSignals(False)
        self._apply_mesh_mode_from_checkboxes()
        self.mesh_material_changed.emit()

    def _on_project_toggled(self, checked):
        if checked:
            self.photographic_checkbox.blockSignals(True)
            self.photographic_checkbox.setChecked(False)
            self.photographic_checkbox.blockSignals(False)
        elif not self.photographic_checkbox.isChecked():
            self.photographic_checkbox.blockSignals(True)
            self.photographic_checkbox.setChecked(True)
            self.photographic_checkbox.blockSignals(False)
        self._apply_mesh_mode_from_checkboxes()
        self.mesh_material_changed.emit()

    def _on_opacity_changed(self, value):
        state_manager.mesh_opacity = value
        self.mesh_opacity_changed.emit(value)

    def _on_mesh_upload_clicked(self):
        mesh_path = open_file_dialog(
            parent=self,
            title="Select a mesh file",
            file_filter=("Wavefront OBJ (*.obj);; All Files (*.*)"),
        )
        if not mesh_path:
            return
        texture_path = open_file_dialog(
            parent=self,
            title="Select a texture image",
            file_filter=(
                "Images (*.jpg *.jpeg *.png);; JPEG (*.jpg *.jpeg);; "
                "PNG (*.png);; All Files (*.*)"
            ),
        )
        if not texture_path:
            return
        input_manager.add_mesh(mesh_path, texture_path)
        self.refresh_mesh_lists()
        self.mesh_changed.emit()

    def _on_mesh_dropdown_changed(self, index):
        if index < 0 or not input_manager.has_mesh:
            return
        input_manager.set_current_mesh_pair(index)
        self.mesh_changed.emit()

    def _on_remove_mesh_clicked(self):
        if not input_manager.has_mesh:
            return
        idx = input_manager.current_mesh_index
        if idx < 0:
            return
        input_manager.remove_mesh_pair(idx)
        self.refresh_mesh_lists()
        self.mesh_changed.emit()

    def refresh_mesh_lists(self):
        mesh_paths = input_manager.provided_mesh_paths
        tex_paths = input_manager.provided_mesh_texture_paths

        try:
            cur_mesh, _cur_tex = input_manager.get_current_mesh_pair_paths()
        except ValueError:
            cur_mesh = None

        mesh_items = [
            self.mesh_dropdown.itemData(i, Qt.UserRole)
            for i in range(self.mesh_dropdown.count())
        ]
        if mesh_items == mesh_paths:
            self._set_mesh_current_path(cur_mesh)
        else:
            self.mesh_dropdown.blockSignals(True)
            self.mesh_dropdown.clear()
            for mp, _tp in zip(mesh_paths, tex_paths):
                self.mesh_dropdown.addItem(Path(mp).name, mp)
            self.mesh_dropdown.blockSignals(False)
            self._set_mesh_current_path(cur_mesh)
        self._sync_mesh_visibility_appearance()
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(state_manager.mesh_opacity)
        self.opacity_slider.blockSignals(False)

    def _set_mesh_current_path(self, current_mesh_path):
        self.mesh_dropdown.blockSignals(True)
        try:
            if not current_mesh_path:
                self.mesh_dropdown.setCurrentIndex(-1)
            else:
                idx = self.mesh_dropdown.findData(current_mesh_path, Qt.UserRole)
                self.mesh_dropdown.setCurrentIndex(idx)
        finally:
            self.mesh_dropdown.blockSignals(False)
        self._schedule_mesh_dropdown_scroll()

    def sync_mesh_visibility_button(self):
        """Update eye icon from the current mesh visibility in the scene."""
        self._sync_mesh_visibility_appearance()


class ParcelInputWidget(QFrame):
    """Widget for parcel CSV inputs (space-separated points and colors)."""

    parcel_changed = Signal()
    parcel_visibility_changed = Signal()
    parcel_size_changed = Signal(int)

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("parcelInputWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        self.title = QLabel("PARCELS")
        self.title.setObjectName("parcelTitle")
        self.main_layout.addWidget(self.title)

        std_h = 38

        self.parcel_row = QHBoxLayout()
        self.parcel_row.setSpacing(8)
        self.parcel_row.setContentsMargins(8, 0, 8, 0)

        self.parcel_upload_button = QPushButton("")
        self.parcel_upload_button.setIcon(QIcon(str(ICONS_PATH / "upload.svg")))
        self.parcel_upload_button.setIconSize(QSize(16, 16))
        self.parcel_upload_button.setObjectName("uploadButton")
        self.parcel_upload_button.setFixedSize(std_h, std_h)
        self.parcel_upload_button.setToolTip(
            "Load parcel file (space-separated values)"
        )
        self.parcel_row.addWidget(self.parcel_upload_button)

        self.parcel_dropdown = QComboBox()
        self.parcel_dropdown.setObjectName("parcelInputDropdown")
        self.parcel_dropdown.setFixedHeight(std_h)
        self.parcel_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.parcel_dropdown.setEditable(True)
        self.parcel_row.addWidget(self.parcel_dropdown)
        _ple = self.parcel_dropdown.lineEdit()
        if _ple is not None:
            _ple.setObjectName("parcelInputDropdownLineEdit")

        self.parcel_visibility_button = QPushButton("")
        self.parcel_visibility_button.setObjectName("parcelVisibilityButton")
        self.parcel_visibility_button.setIcon(QIcon(str(ICONS_PATH / "eye.svg")))
        self.parcel_visibility_button.setIconSize(QSize(18, 18))
        self.parcel_visibility_button.setFixedSize(std_h, std_h)
        self.parcel_visibility_effect = QGraphicsOpacityEffect(
            self.parcel_visibility_button
        )
        self.parcel_visibility_button.setGraphicsEffect(self.parcel_visibility_effect)
        self.parcel_row.addWidget(self.parcel_visibility_button)

        self.parcel_remove_button = QPushButton("×")
        self.parcel_remove_button.setObjectName("parcelRemoveButton")
        self.parcel_remove_button.setFixedSize(std_h, std_h)
        self.parcel_row.addWidget(self.parcel_remove_button)

        self.main_layout.addLayout(self.parcel_row)

        self._parcel_controls = QWidget()
        self._parcel_controls.setObjectName("parcelExtraControls")
        parcel_controls_layout = QVBoxLayout(self._parcel_controls)
        parcel_controls_layout.setContentsMargins(0, 0, 0, 0)
        parcel_controls_layout.setSpacing(8)

        opacity_header = QHBoxLayout()
        self.opacity_label = QLabel("Opacity")
        self.opacity_label.setObjectName("parcelOpacityLabel")
        self.opacity_label.setToolTip("Controls parcel point size (0–100).")
        opacity_header.addWidget(self.opacity_label)
        opacity_header.addStretch()
        parcel_controls_layout.addLayout(opacity_header)

        opacity_slider_row = QHBoxLayout()
        self.opacity_min_label = QLabel("0")
        self.opacity_min_label.setObjectName("parcelOpacityTickLabel")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setObjectName("parcelOpacitySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Controls parcel point size (0–100).")
        self.opacity_max_label = QLabel("100")
        self.opacity_max_label.setObjectName("parcelOpacityTickLabel")
        opacity_slider_row.addWidget(self.opacity_min_label)
        opacity_slider_row.addWidget(self.opacity_slider)
        opacity_slider_row.addWidget(self.opacity_max_label)
        parcel_controls_layout.addLayout(opacity_slider_row)

        self.main_layout.addWidget(self._parcel_controls)

        self.parcel_upload_button.setCursor(Qt.PointingHandCursor)
        self.parcel_visibility_button.setCursor(Qt.PointingHandCursor)
        self.parcel_remove_button.setCursor(Qt.PointingHandCursor)

        self.parcel_upload_button.clicked.connect(self._on_parcel_upload_clicked)
        self.parcel_dropdown.currentIndexChanged.connect(
            self._on_parcel_dropdown_changed
        )
        self.parcel_visibility_button.clicked.connect(
            self._on_parcel_visibility_clicked
        )
        self.parcel_remove_button.clicked.connect(self._on_remove_parcel_clicked)
        self.opacity_slider.valueChanged.connect(self._on_size_changed)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refresh_parcel_lists)
        self._poll_timer.start()

        self.refresh_parcel_lists()
        self._sync_parcel_visibility_appearance()

    def _scroll_parcel_dropdown_to_start(self):
        le = self.parcel_dropdown.lineEdit()
        if le is not None:
            le.setCursorPosition(0)
            le.deselect()

    def _schedule_parcel_dropdown_scroll(self):
        QTimer.singleShot(0, self._scroll_parcel_dropdown_to_start)

    def _on_parcel_visibility_clicked(self):
        visualization_manager.toggle_parcel_visibility()
        self._sync_parcel_visibility_appearance()
        self.parcel_visibility_changed.emit()

    def _sync_parcel_visibility_appearance(self):
        has_parcel = input_manager.has_parcel
        self.parcel_visibility_button.setVisible(has_parcel)
        self.parcel_remove_button.setEnabled(has_parcel)
        self._update_parcel_controls_visibility()
        if not has_parcel:
            return
        if visualization_manager.parcel_is_visible:
            self.parcel_visibility_effect.setOpacity(1.0)
        else:
            self.parcel_visibility_effect.setOpacity(0.42)

    def _update_parcel_controls_visibility(self):
        self._parcel_controls.setVisible(input_manager.has_parcel)

    def _on_size_changed(self, value):
        state_manager.parcel_size = value
        self.parcel_size_changed.emit(value)

    def _on_parcel_upload_clicked(self):
        file_path = open_file_dialog(
            parent=self,
            title="Select a parcel file",
            file_filter=(
                "Parcel text / CSV (*.csv *.txt);; "
                "CSV Files (*.csv);; Text Files (*.txt);; All Files (*.*)"
            ),
        )
        if not file_path:
            return
        input_manager.add_parcel(file_path)
        self.refresh_parcel_lists()
        self.parcel_changed.emit()

    def _on_parcel_dropdown_changed(self, index):
        if index < 0 or not input_manager.has_parcel:
            return
        input_manager.set_current_parcel(index)
        self.parcel_changed.emit()

    def _on_remove_parcel_clicked(self):
        if not input_manager.has_parcel:
            return
        idx = input_manager.current_parcel_index
        if idx < 0:
            return
        input_manager.remove_parcel(idx)
        self.refresh_parcel_lists()
        self.parcel_changed.emit()

    def refresh_parcel_lists(self):
        parcel_paths = input_manager.provided_parcel_paths

        try:
            _pts, _colors, cur_path, _idx = input_manager.get_current_parcel()
        except ValueError:
            cur_path = None

        current_items = [
            self.parcel_dropdown.itemData(i, Qt.UserRole)
            for i in range(self.parcel_dropdown.count())
        ]
        if current_items == parcel_paths:
            self._set_parcel_current_path(cur_path)
        else:
            self.parcel_dropdown.blockSignals(True)
            self.parcel_dropdown.clear()
            for path in parcel_paths:
                self.parcel_dropdown.addItem(Path(path).name, path)
            self.parcel_dropdown.blockSignals(False)
            self._set_parcel_current_path(cur_path)
        self._sync_parcel_visibility_appearance()
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(state_manager.parcel_size)
        self.opacity_slider.blockSignals(False)

    def _set_parcel_current_path(self, current_path):
        self.parcel_dropdown.blockSignals(True)
        try:
            if not current_path:
                self.parcel_dropdown.setCurrentIndex(-1)
            else:
                idx = self.parcel_dropdown.findData(current_path, Qt.UserRole)
                self.parcel_dropdown.setCurrentIndex(idx)
        finally:
            self.parcel_dropdown.blockSignals(False)
        self._schedule_parcel_dropdown_scroll()

    def sync_parcel_visibility_button(self):
        """Update eye icon from the current parcel visibility in the scene."""
        self._sync_parcel_visibility_appearance()


class RoiInputWidget(QFrame):
    """Widget for ROI inputs (NIfTI), supporting multiple ROIs.

    The header exposes an upload button and an add (+) placeholder button.
    A global opacity slider is shown only when at least one ROI is loaded,
    and each ROI is represented by a row with a color swatch, the file
    name, a visibility toggle, and a remove button.
    """

    rois_changed = Signal()
    roi_visibility_changed = Signal()
    roi_opacity_changed = Signal(int)
    roi_create_requested = Signal()

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("roiInputWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        self.title = QLabel("ROI")
        self.title.setObjectName("roiTitle")
        self.main_layout.addWidget(self.title)

        std_h = 38

        self.header_row = QHBoxLayout()
        self.header_row.setSpacing(8)
        self.header_row.setContentsMargins(8, 0, 8, 0)

        self.upload_button = QPushButton("")
        self.upload_button.setIcon(QIcon(str(ICONS_PATH / "upload.svg")))
        self.upload_button.setIconSize(QSize(16, 16))
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.setFixedSize(std_h, std_h)
        self.upload_button.setToolTip("Upload ROI from file")
        self.header_row.addWidget(self.upload_button)

        self.add_button = QPushButton("+")
        self.add_button.setObjectName("roiAddButton")
        self.add_button.setFixedSize(std_h, std_h)
        self.add_button.setToolTip("Add a new ROI")
        self.header_row.addWidget(self.add_button)

        self.header_row.addStretch()
        self.main_layout.addLayout(self.header_row)

        self._roi_controls = QWidget()
        self._roi_controls.setObjectName("roiExtraControls")
        roi_controls_layout = QVBoxLayout(self._roi_controls)
        roi_controls_layout.setContentsMargins(0, 0, 0, 0)
        roi_controls_layout.setSpacing(8)

        opacity_header = QHBoxLayout()
        self.opacity_label = QLabel("Opacity")
        self.opacity_label.setObjectName("roiOpacityLabel")
        opacity_header.addWidget(self.opacity_label)
        opacity_header.addStretch()
        roi_controls_layout.addLayout(opacity_header)

        opacity_slider_row = QHBoxLayout()
        self.opacity_min_label = QLabel("0")
        self.opacity_min_label.setObjectName("roiOpacityTickLabel")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setObjectName("roiOpacitySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(state_manager.roi_opacity)
        self.opacity_max_label = QLabel("100")
        self.opacity_max_label.setObjectName("roiOpacityTickLabel")
        opacity_slider_row.addWidget(self.opacity_min_label)
        opacity_slider_row.addWidget(self.opacity_slider)
        opacity_slider_row.addWidget(self.opacity_max_label)
        roi_controls_layout.addLayout(opacity_slider_row)

        self._rows_container = QWidget()
        self._rows_container.setObjectName("roiRowsContainer")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        roi_controls_layout.addWidget(self._rows_container)

        self.main_layout.addWidget(self._roi_controls)

        self._row_widgets = []

        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refresh_rois)
        self._poll_timer.start()

        self.refresh_rois()

    def resizeEvent(self, event):
        """Re-elide ROI row labels when the widget width changes.

        Parameters
        ----------
        event : QResizeEvent
            The resize event delivered by Qt.
        """
        super().resizeEvent(event)
        for index in range(len(self._row_widgets)):
            self._sync_row_appearance(index)

    def _on_upload_clicked(self):
        """Upload an ROI NIfTI file and add it to the input manager."""
        file_path = open_file_dialog(
            parent=self,
            title="Select an ROI file",
            file_filter=(
                "NIfTI Files (*.nii *.nii.gz);; NII Files (*.nii);; "
                "NII.GZ Files (*.nii.gz);; All Files (*.*)"
            ),
        )
        if not file_path:
            return
        input_manager.add_roi(file_path)
        self.rois_changed.emit()
        self.refresh_rois()

    def _on_add_clicked(self):
        """Enter the interactive ROI create mode.

        Drawing requires a T1 image to anchor the slice plane. When no
        T1 is loaded the button only flashes a tooltip instead of
        emitting the request signal.
        """
        if not input_manager.has_t1:
            self.add_button.setToolTip("Load a T1 image first to draw an ROI")
            return
        self.add_button.setToolTip("Add a new ROI")
        self.roi_create_requested.emit()

    def _on_opacity_changed(self, value):
        """Update opacity for every ROI actor.

        Parameters
        ----------
        value : int
            The slider value (0-100).
        """
        visualization_manager.set_roi_opacity(value)
        self.roi_opacity_changed.emit(value)

    def _on_visibility_clicked(self, index):
        """Toggle scene visibility of the ROI at ``index``.

        Parameters
        ----------
        index : int
            Index of the ROI row whose visibility should flip.
        """
        visualization_manager.toggle_roi_visibility_at(index)
        self._sync_row_appearance(index)
        self.roi_visibility_changed.emit()

    def _on_apply_clicked(self, index):
        """Toggle whether the ROI at ``index`` contributes to the filter.

        Parameters
        ----------
        index : int
            Index of the ROI row whose applied flag should flip.
        """
        if index < 0:
            return
        visualization_manager.toggle_roi_applied_at(index)
        self._sync_row_appearance(index)
        self.rois_changed.emit()

    def _on_negate_clicked(self, index):
        """Toggle filter negation for the ROI at ``index``.

        Parameters
        ----------
        index : int
            Index of the ROI row whose negation flag should flip.
        """
        if index < 0:
            return
        visualization_manager.toggle_roi_negated_at(index)
        self._sync_row_appearance(index)
        self.rois_changed.emit()

    def _on_remove_clicked(self, index):
        """Remove the ROI at ``index`` from the input manager.

        Parameters
        ----------
        index : int
            Index of the ROI row to remove.
        """
        if index < 0:
            return
        input_manager.remove_roi(index)
        self.rois_changed.emit()
        self.refresh_rois()

    def _sync_row_appearance(self, index):
        """Dim each per-row button to reflect its current ROI state.

        Parameters
        ----------
        index : int
            Index of the ROI row to refresh.
        """
        if index < 0 or index >= len(self._row_widgets):
            return
        row = self._row_widgets[index]
        row["visibility_effect"].setOpacity(
            1.0 if visualization_manager.is_roi_visible_at(index) else 0.42
        )
        row["apply_effect"].setOpacity(
            1.0 if visualization_manager.is_roi_applied_at(index) else 0.42
        )
        row["negate_effect"].setOpacity(
            1.0 if visualization_manager.is_roi_negated_at(index) else 0.42
        )
        width = row["label"].width()
        if width > 0:
            row["label"].setText(
                row["label"]
                .fontMetrics()
                .elidedText(row["full_name"], Qt.ElideRight, width)
            )
        else:
            row["label"].setText(row["full_name"])

    def _make_icon_button(self, *, object_name, icon_path=None, text="", tooltip=""):
        """Create a small square icon button used inside an ROI row.

        ``QToolButton`` is used instead of ``QPushButton`` because the latter
        reserves font-metric space even for icon-only buttons, which pushes
        the icon below the geometric center.

        Parameters
        ----------
        object_name : str
            Qt object name applied to the button for QSS targeting.
        icon_path : str or None, optional
            Filesystem path to an SVG icon. If None, ``text`` is used instead.
        text : str, optional
            Fallback label drawn on the button when ``icon_path`` is None.
        tooltip : str, optional
            Hover tooltip describing the action.

        Returns
        -------
        tuple[QToolButton, QGraphicsOpacityEffect]
            The button and its attached opacity effect for dimming.
        """
        button = QToolButton()
        button.setObjectName(object_name)
        if icon_path is not None:
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(16, 16))
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        elif text:
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setAutoRaise(True)
        button.setFixedSize(28, 28)
        button.setCursor(Qt.PointingHandCursor)
        if tooltip:
            button.setToolTip(tooltip)
        effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(effect)
        return button, effect

    def _build_row(self, index, name, color):
        """Build a single ROI row.

        Parameters
        ----------
        index : int
            Initial position of the row in the widget list.
        name : str
            ROI display name (typically the file basename).
        color : tuple of float or None
            RGB color (each in [0, 1]) used for the swatch.

        Returns
        -------
        dict
            Row metadata used by ``refresh_rois`` and the sync helpers.
        """
        row_widget = QWidget()
        row_widget.setObjectName("roiRow")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        swatch = QLabel()
        swatch.setObjectName("roiSwatch")
        swatch.setFixedSize(6, 28)
        if color is not None:
            r, g, b = (int(round(c * 255)) for c in color)
            swatch.setStyleSheet(
                f"background-color: rgb({r}, {g}, {b}); border-radius: 2px;"
            )
        row_layout.addWidget(swatch)

        label = QLabel(name)
        label.setObjectName("roiRowLabel")
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        label.setMinimumWidth(40)
        label.setToolTip(name)
        row_layout.addWidget(label, 1)

        visibility_button, visibility_effect = self._make_icon_button(
            object_name="roiVisibilityButton",
            icon_path=str(ICONS_PATH / "eye.svg"),
            tooltip="Show/hide ROI",
        )
        visibility_button.clicked.connect(
            lambda _checked=False, w=row_widget: self._on_visibility_clicked(
                self._row_index(w)
            )
        )
        row_layout.addWidget(visibility_button)

        apply_button, apply_effect = self._make_icon_button(
            object_name="roiApplyButton",
            icon_path=str(ICONS_PATH / "check.svg"),
            tooltip="Apply ROI as a streamline filter",
        )
        apply_button.clicked.connect(
            lambda _checked=False, w=row_widget: self._on_apply_clicked(
                self._row_index(w)
            )
        )
        row_layout.addWidget(apply_button)

        negate_button, negate_effect = self._make_icon_button(
            object_name="roiNegateButton",
            icon_path=str(ICONS_PATH / "negation.svg"),
            tooltip="Negate ROI in the filter",
        )
        negate_button.clicked.connect(
            lambda _checked=False, w=row_widget: self._on_negate_clicked(
                self._row_index(w)
            )
        )
        row_layout.addWidget(negate_button)

        remove_button, _remove_effect = self._make_icon_button(
            object_name="roiRemoveButton",
            text="✕",
            tooltip="Remove ROI",
        )
        remove_button.clicked.connect(
            lambda _checked=False, w=row_widget: self._on_remove_clicked(
                self._row_index(w)
            )
        )
        row_layout.addWidget(remove_button)

        return {
            "widget": row_widget,
            "label": label,
            "full_name": name,
            "swatch": swatch,
            "visibility_button": visibility_button,
            "visibility_effect": visibility_effect,
            "apply_button": apply_button,
            "apply_effect": apply_effect,
            "negate_button": negate_button,
            "negate_effect": negate_effect,
            "remove_button": remove_button,
        }

    def _row_index(self, row_widget):
        """Return the current index of a row widget, or -1 if absent."""
        for idx, row in enumerate(self._row_widgets):
            if row["widget"] is row_widget:
                return idx
        return -1

    def refresh_rois(self):
        """Synchronize the row list with input/visualization managers.

        Rows are rebuilt only when the underlying ROI path list changes;
        otherwise just the visibility indicators are updated to keep the
        polling timer cheap.
        """
        roi_paths = input_manager.provided_roi_paths
        cached_paths = [row.get("path") for row in self._row_widgets]
        if cached_paths != roi_paths:
            for row in self._row_widgets:
                self._rows_layout.removeWidget(row["widget"])
                row["widget"].deleteLater()
            self._row_widgets = []

            for index, path in enumerate(roi_paths):
                color = visualization_manager.get_roi_color(index)
                row = self._build_row(index, Path(path).name, color)
                row["path"] = path
                self._rows_layout.addWidget(row["widget"])
                self._row_widgets.append(row)

        for index in range(len(self._row_widgets)):
            self._sync_row_appearance(index)

        has_roi = bool(roi_paths)
        self._roi_controls.setVisible(has_roi)

        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(state_manager.roi_opacity)
        self.opacity_slider.blockSignals(False)


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

        self.mesh_input_widget = MeshInputWidget(parent=self)
        self.main_layout.addWidget(self.mesh_input_widget)

        self.parcel_input_widget = ParcelInputWidget(parent=self)
        self.main_layout.addWidget(self.parcel_input_widget)
