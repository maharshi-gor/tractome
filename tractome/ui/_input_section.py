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
