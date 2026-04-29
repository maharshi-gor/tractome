from PySide6.QtCore import QTimer, Qt
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
import numpy as np

from tractome.mem import input_manager, state_manager, visualization_manager
from tractome.ui._control_section import LeftSectionWidget
from tractome.ui._input_section import RightSectionWidget
from tractome.ui._paths import IMAGES_PATH
from tractome.ui._visualization_section import CenterSectionWidget
from tractome.ui.utils import open_file_dialog
from tractome.viz import rasterize_cylinder, rasterize_sphere


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
        self._left_section.roi_input_widget.roi_create_requested.connect(
            self._on_roi_create_requested
        )
        self._left_section.roi_create_widget.shape_changed.connect(
            self._on_roi_create_shape_changed
        )
        self._left_section.roi_create_widget.edit_requested.connect(
            self._on_roi_create_edit_requested
        )
        self._center_section.roi_drawn.connect(self._on_roi_drawn)
        self._draft_roi_id = None
        # ROI synthetic id -> last shape rasterized for it ("sphere"
        # or "cylinder"). Decoupled from the synthetic id so an ROI
        # can change shape without being renamed.
        self._roi_shape_by_id = {}
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

        # The 2D scene caches its own T1/ROI/projection actors built
        # from the previously-current T1; without this rebuild a subject
        # change made while in 2D mode keeps the old image on screen
        # until the user toggles 3D→2D (which calls the same rebuild
        # via _on_view_mode_changed). The new T1's bounding box also
        # differs, so the camera needs to be re-framed against the new
        # actor, otherwise it would still be sized for the previous one.
        if state_manager.view_mode == "2D":
            self._build_2d_scene_contents()
            self._center_section.orient_2d_camera_to_active_slice()
            self._center_section.show_manager.render()

    def _on_t1_visibility_changed(self):
        """Re-render after toggling T1 visibility in the scene.

        In 2D mode the same signal also fires when the user picks a new
        active axis via the radio buttons, so the orthographic camera is
        re-aimed at the new slice plane before rendering. Without this
        the camera keeps the orientation it had when 2D mode was first
        entered and the new plane shows up edge-on.
        """
        if state_manager.view_mode == "2D":
            self._center_section.orient_2d_camera_to_active_slice()
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

    def _on_roi_create_requested(self):
        """Switch to 2D mode and start the interactive ROI draw."""
        if not input_manager.has_t1:
            return
        if state_manager.view_mode != "2D":
            self._left_section.view_mode_widget.set_mode("2D")
            self._on_view_mode_changed("2D")
        shape = self._left_section.roi_create_widget.current_shape()
        self._center_section.enter_roi_create_mode(shape)
        self._draft_roi_id = None
        self._left_section.update_controls_for_visualization()
        # Re-entering create mode shows every ROI drawn in earlier
        # sessions; the user can pick one to edit instead of starting
        # a new ROI from scratch.
        self._left_section.roi_create_widget.clear_existing_selection()
        self._refresh_roi_create_existing_list()

    def _refresh_roi_create_existing_list(self):
        """Push the current set of ROIs into the create panel's list.

        The list mirrors ``input_manager.provided_roi_paths`` and is
        called whenever the set of ROIs changes (entering create
        mode, after each draw, after an edit-target change). Color
        comes from the visualization manager so the swatches in the
        list match the contours in the 3D scene.
        """
        items = []
        for index, name in enumerate(input_manager.provided_roi_paths):
            color = visualization_manager.get_roi_color(index)
            items.append({"name": str(name), "color": color})
        self._left_section.roi_create_widget.refresh_existing_rois(items)

    def _on_roi_create_shape_changed(self, shape):
        """Update the active shape used by the next drag.

        The draft pointer is intentionally **kept**: switching from
        sphere to cylinder (or back) on the same draft replaces that
        ROI's volume with the new primitive on the next drag, rather
        than spawning a third entry. To start a fresh ROI the user
        clears the existing-ROIs selection.
        """
        self._center_section.set_roi_create_shape(shape)

    def _on_roi_create_edit_requested(self, name):
        """Make the selected existing ROI the active edit target.

        ``name`` is the synthetic id stored in input_manager; an empty
        string means "no selection — next drag creates a new ROI".
        Setting the draft pointer to an existing ROI is all we need:
        the next drag flows through ``update_roi_volume`` and rewrites
        that ROI in place. We also push the selected ROI's metadata
        into the Properties pane so the user sees what they're editing.
        """
        if not name:
            self._draft_roi_id = None
            self._left_section.roi_create_widget.reset_properties()
            return

        roi_paths = list(input_manager.provided_roi_paths)
        if name not in roi_paths:
            self._draft_roi_id = None
            self._left_section.roi_create_widget.reset_properties()
            return

        index = roi_paths.index(name)
        self._draft_roi_id = name
        try:
            volume, _, _, _ = input_manager.get_roi_at(index)
        except ValueError:
            volume = None
        if volume is not None:
            try:
                import numpy as np  # local: shadow not desired at module scope

                ix, iy, iz = np.where(volume > 0)
                voxel_pos = (ix.mean(), iy.mean(), iz.mean()) if len(ix) else None
            except Exception:
                voxel_pos = None
        else:
            voxel_pos = None
        # The synthetic id is now shape-agnostic ("ROI N"); the
        # actual shape is read from the side-table populated each
        # time a draft is rasterized.
        shape = self._roi_shape_by_id.get(name)
        type_ = shape.capitalize() if shape else "–"
        color = visualization_manager.get_roi_color(index)
        self._left_section.roi_create_widget.set_properties(
            name=name,
            visibility=True,
            type_=type_,
            position=voxel_pos,
            color=color,
        )

    def _commit_roi_create_session(self):
        """Finish a create-mode session: exit mode + apply filter.

        Single-ROI-per-session: any ROIs drawn in this session stay
        in the input manager; the draft pointer is cleared, the
        center-section drag handlers are removed, and the streamline
        filter + recluster runs once so the 3D tractogram view
        reflects whatever was drawn.
        """
        was_create_mode = state_manager.roi_create_mode is not None
        had_draft = self._draft_roi_id is not None
        self._draft_roi_id = None
        self._center_section.exit_roi_create_mode()
        self._left_section.roi_create_widget.reset_properties()
        self._left_section.update_controls_for_visualization()
        self._left_section.roi_input_widget.refresh_rois()
        # Only run the (potentially expensive) filter + recluster if
        # we were actually in create mode AND the user committed at
        # least one drag in this session. A no-op session shouldn't
        # trigger reclustering.
        if was_create_mode and had_draft and input_manager.has_roi:
            self._on_rois_changed()

    def _on_roi_drawn(self, world_center, world_radius, shape):
        """Rasterize the drawn shape into a binary volume.

        Behaviour: while the user keeps drawing without clicking
        ``New`` or ``Save`` the same draft ROI is overwritten in
        place. Clicking ``New`` clears the draft pointer so the next
        drag lands as a fresh entry. ``Save`` is what triggers the
        filter + recluster pass; this method never runs that pipeline.
        """
        if not input_manager.has_t1:
            return
        t1_volume, affine, _, _ = input_manager.get_current_t1()
        shape_volume = t1_volume.shape

        slice_axis = None
        for index, value in enumerate(state_manager.t1_slice_visibility_2d):
            if value:
                slice_axis = index
                break

        if shape == "cylinder" and slice_axis is not None:
            # The cylinder runs perpendicular to the active slice and
            # should span the full T1 along that axis (the user is
            # carving a tube through the whole brain, not just one
            # slab). World extent along the axis = nb_voxels * voxel
            # spacing. We pass 2x that so the cylinder definitely
            # covers the volume regardless of where the click landed
            # — rasterize_cylinder already clips to the volume
            # bounds, so the 2x is free.
            spacing = float(np.linalg.norm(affine[:3, slice_axis]))
            full_extent = float(shape_volume[slice_axis]) * spacing
            world_height = max(2.0 * full_extent, 1.0)
            volume = rasterize_cylinder(
                shape_volume,
                affine,
                world_center,
                float(world_radius),
                slice_axis,
                world_height,
            )
        else:
            volume = rasterize_sphere(
                shape_volume,
                affine,
                world_center,
                float(world_radius),
            )

        if not np.any(volume):
            return

        if self._draft_roi_id is None:
            self._draft_roi_id = input_manager.add_roi_volume(
                volume, affine, label=shape
            )
        else:
            input_manager.update_roi_volume(self._draft_roi_id, volume, affine)
        # Remember the shape that was rasterized so the Properties
        # pane (and a later edit-target switch) can show the right
        # Type without having to parse the synthetic id.
        self._roi_shape_by_id[self._draft_roi_id] = shape

        # Refresh ROI actors only — filter + recluster is deferred
        # until the user leaves create mode (handled by
        # _commit_roi_create_session). visualize_rois() rebuilds all
        # contours; for the draft case that's just one cheap
        # marching-cubes run, not the full clustering pipeline.
        roi_viz = list(visualization_manager.roi_visualizations)
        if roi_viz:
            self._center_section.remove_visualization(roi_viz, visualization_type="roi")
        roi_vis = visualization_manager.visualize_rois()
        if roi_vis:
            self._center_section.add_visualization(roi_vis, visualization_type="roi")

        self._center_section.remove_2d_visualization(
            visualization_manager.roi_2d_visualizations
        )
        roi_2d = visualization_manager.visualize_rois_2d()
        if roi_2d:
            self._center_section.add_2d_visualization(roi_2d)

        # pygfx commits scene-graph changes one frame late (same
        # workaround as set_view_mode), so schedule a deferred render
        # to make the new slicer visible without a 3D/2D toggle.
        self._center_section.show_manager.render()
        QTimer.singleShot(0, self._center_section.show_manager.render)

        # Push the active ROI's metadata into the Properties pane.
        # Voxel position uses the volume centroid so it stays
        # meaningful as the user re-drags the same draft.
        try:
            ix, iy, iz = np.where(volume > 0)
            voxel_pos = (ix.mean(), iy.mean(), iz.mean())
        except Exception:
            voxel_pos = None
        roi_index = next(
            (
                i
                for i, p in enumerate(input_manager.provided_roi_paths)
                if p == self._draft_roi_id
            ),
            -1,
        )
        color = visualization_manager.get_roi_color(roi_index)
        self._left_section.roi_create_widget.set_properties(
            name=self._draft_roi_id or "–",
            visibility=True,
            type_=shape.capitalize() if shape else "–",
            position=voxel_pos,
            color=color,
        )
        # Newly-added ROIs need to appear in the existing-ROIs list
        # immediately; updates to an existing draft re-emit the same
        # name so the list still refreshes (cheap — just rebuilds N
        # rows in a QListWidget).
        self._refresh_roi_create_existing_list()

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

        # Leaving create mode for 3D commits the session: any drawn
        # ROI is finalized, the panel resets, and the streamline
        # filter + recluster runs once so the 3D tractogram view
        # reflects the new ROI. This is the only place the filter
        # runs during a create session — per-draw refreshes never
        # touch the cluster pipeline.
        if state_manager.roi_create_mode is not None and mode == "3D":
            self._commit_roi_create_session()

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
