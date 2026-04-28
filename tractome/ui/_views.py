from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tractome.mem import input_manager, state_manager, visualization_manager
from tractome.ui._control_section import LeftSectionWidget
from tractome.ui._input_section import RightSectionWidget
from tractome.ui._paths import IMAGES_PATH
from tractome.ui._visualization_section import CenterSectionWidget
from tractome.ui.utils import open_file_dialog


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
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        self._left_section = LeftSectionWidget(parent=self)
        self._center_section = CenterSectionWidget()
        self._right_section = RightSectionWidget()
        self._right_section.image_input_widget.t1_changed.connect(self._on_t1_changed)
        self._right_section.image_input_widget.t1_visibility_changed.connect(
            self._on_t1_visibility_changed
        )
        self._right_section.image_input_widget.t1_slices_changed.connect(
            self._on_t1_slices_changed
        )
        self._right_section.mesh_input_widget.mesh_changed.connect(
            self._on_mesh_changed
        )
        self._right_section.mesh_input_widget.mesh_visibility_changed.connect(
            self._on_mesh_visibility_changed
        )
        self._right_section.mesh_input_widget.mesh_opacity_changed.connect(
            self._on_mesh_opacity_changed
        )
        self._right_section.mesh_input_widget.mesh_material_changed.connect(
            self._on_mesh_material_changed
        )
        self._right_section.parcel_input_widget.parcel_changed.connect(
            self._on_parcel_changed
        )
        self._right_section.parcel_input_widget.parcel_visibility_changed.connect(
            self._on_parcel_visibility_changed
        )
        self._right_section.parcel_input_widget.parcel_size_changed.connect(
            self._on_parcel_size_changed
        )
        self._left_section.roi_input_widget.rois_changed.connect(self._on_rois_changed)
        self._left_section.roi_input_widget.roi_visibility_changed.connect(
            self._on_roi_visibility_changed
        )
        self._left_section.roi_input_widget.roi_opacity_changed.connect(
            self._on_roi_opacity_changed
        )
        self._left_section.view_mode_widget.view_mode_changed.connect(
            self._on_view_mode_changed
        )

        main_layout.addWidget(self._left_section, 1)
        main_layout.addWidget(self._center_section, 3)
        main_layout.addWidget(self._right_section, 1)

    def _on_t1_changed(self):
        """Refresh T1 visualization and reset slices for current T1."""
        if visualization_manager.t1_visualizations:
            self.remove_visualization(
                visualization_manager.t1_visualizations, visualization_type="t1"
            )

        t1_visualization = visualization_manager.visualize_t1()
        if t1_visualization is not None:
            self.add_visualization(t1_visualization, visualization_type="t1")
            self._right_section.image_input_widget.configure_t1_slice_controls()
            self._right_section.image_input_widget.emit_current_slices()
        self._right_section.image_input_widget.sync_t1_visibility_button()

    def _on_t1_visibility_changed(self):
        """Re-render after toggling T1 visibility in the scene."""
        self._center_section.show_manager.render()

    def _on_t1_slices_changed(self, x, y, z):
        """Update shown T1 slices from the input controls."""
        visualization_manager.show_t1_slices(x, y, z)
        self._center_section.show_manager.render()

    def _on_mesh_changed(self):
        """Reload mesh actor when the mesh/texture pair changes."""
        mesh_viz = visualization_manager.mesh_visualizations
        if mesh_viz:
            self.remove_visualization(mesh_viz, visualization_type="mesh")
        mesh_vis = visualization_manager.visualize_mesh()
        if mesh_vis is not None:
            self.add_visualization(mesh_vis, visualization_type="mesh")
        self._right_section.mesh_input_widget.sync_mesh_visibility_button()

    def _on_mesh_visibility_changed(self):
        """Re-render after toggling mesh visibility."""
        self._center_section.show_manager.render()

    def _on_mesh_opacity_changed(self, value):
        """Apply mesh opacity from the slider."""
        visualization_manager.set_mesh_opacity(value)
        self._center_section.show_manager.render()

    def _on_mesh_material_changed(self):
        """Rebuild mesh when Photographic/Project material mode changes."""
        if not input_manager.has_mesh:
            return
        mesh_viz = visualization_manager.mesh_visualizations
        if mesh_viz:
            self.remove_visualization(mesh_viz, visualization_type="mesh")
        mesh_vis = visualization_manager.visualize_mesh()
        if mesh_vis is not None:
            self.add_visualization(mesh_vis, visualization_type="mesh")
        self._right_section.mesh_input_widget.sync_mesh_visibility_button()

    def _on_parcel_changed(self):
        """Reload parcel actor when the file selection changes."""
        parcel_viz = visualization_manager.parcel_visualizations
        if parcel_viz:
            self.remove_visualization(parcel_viz, visualization_type="parcel")
        parcel_vis = visualization_manager.visualize_parcel()
        if parcel_vis is not None:
            self.add_visualization(parcel_vis, visualization_type="parcel")
        self._right_section.parcel_input_widget.sync_parcel_visibility_button()

    def _on_parcel_visibility_changed(self):
        """Re-render after toggling parcel visibility."""
        self._center_section.show_manager.render()

    def _on_parcel_size_changed(self, value):
        """Apply parcel point size from the slider (labeled Opacity in the UI)."""
        visualization_manager.set_parcel_size(value)
        self._center_section.show_manager.render()

    def _on_rois_changed(self):
        """Rebuild the ROI visualization and re-filter streamlines.

        Also re-clusters the tractogram on the filtered set when the
        filter changes so the scene reflects the new ROI selection.
        """
        roi_viz = list(visualization_manager.roi_visualizations)
        if roi_viz:
            self.remove_visualization(roi_viz, visualization_type="roi")
        roi_vis = visualization_manager.visualize_rois()
        if roi_vis:
            self.add_visualization(roi_vis, visualization_type="roi")
        self._left_section.roi_input_widget.refresh_rois()

        if visualization_manager.apply_roi_filter():
            tractogram_viz = list(visualization_manager.tractogram_visualizations or [])
            if tractogram_viz:
                self.remove_visualization(
                    tractogram_viz, visualization_type="tractogram"
                )
            nb_clusters = (
                state_manager.get_latest_state().nb_clusters
                if state_manager.has_states()
                else 100
            )
            tractogram_vis = visualization_manager.visualize_tractogram(
                nb_clusters=nb_clusters
            )
            if tractogram_vis is not None:
                self.add_visualization(tractogram_vis, visualization_type="tractogram")

    def _on_roi_visibility_changed(self):
        """Re-render after toggling per-ROI visibility."""
        self._center_section.show_manager.render()

    def _on_roi_opacity_changed(self, _value):
        """Re-render after the ROI opacity slider moves."""
        self._center_section.show_manager.render()

    def _on_view_mode_changed(self, mode):
        """Switch the active scene and matching control panels for ``mode``.

        Building the 2D scene is deferred to the first 2D toggle: the
        T1, ROI, and projection actors required for orthographic viewing
        are only constructed when the user opts in.

        Parameters
        ----------
        mode : str
            Either ``"3D"`` or ``"2D"``.
        """
        if state_manager.view_mode == mode:
            return

        state_manager.view_mode = mode
        if mode == "2D":
            self._build_2d_scene_contents()
            self._right_section.mesh_input_widget.setVisible(False)
            self._right_section.parcel_input_widget.setVisible(False)
            self._right_section.image_input_widget.set_slice_control_mode("radio")
        else:
            self._right_section.mesh_input_widget.setVisible(True)
            self._right_section.parcel_input_widget.setVisible(True)
            self._right_section.image_input_widget.set_slice_control_mode("checkbox")

        self._center_section.set_view_mode(mode)
        self._left_section.update_controls_for_visualization()

    def _build_2d_scene_contents(self):
        """Rebuild the actors that belong to the 2D scene.

        Existing 2D T1 / ROI / streamline actors are removed first so the
        2D scene reflects the current data and selection. The streamline
        projections are recomputed from the latest cluster selection.
        """
        center = self._center_section
        center.remove_2d_visualization(visualization_manager.t1_2d_visualizations)
        center.remove_2d_visualization(visualization_manager.roi_2d_visualizations)
        center.remove_2d_visualization(
            visualization_manager.streamlines_2d_visualizations
        )

        t1_2d = visualization_manager.visualize_t1_2d()
        if t1_2d:
            center.add_2d_visualization(t1_2d)

        roi_2d = visualization_manager.visualize_rois_2d()
        if roi_2d:
            center.add_2d_visualization(roi_2d)

        projections = visualization_manager.visualize_streamlines_projection_2d()
        if projections:
            center.add_2d_visualization(projections)

    def add_visualization(self, visualizations, visualization_type="unknown"):
        """Add a visualization to the center section.

        Parameters
        ----------
        visualizations : list
            Visualizations to add.
        visualization_type : str, optional
            Type/category of the visualization payload.
        """
        self._center_section.add_visualization(
            visualizations, visualization_type=visualization_type
        )
        self._left_section.update_controls_for_visualization()
        self._center_section.show_manager.render()

    def remove_visualization(self, visualizations, *, visualization_type="unknown"):
        """Remove a visualization from the center section.

        Parameters
        ----------
        visualizations : list
            Visualizations to remove.
        """
        self._center_section.remove_visualization(
            visualizations, visualization_type=visualization_type
        )
        self._left_section.update_controls_for_visualization()
        self._center_section.show_manager.render()
