from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
import numpy as np

from fury import window
from fury.lib import (
    DirectionalLight,
    Event,
    OrthographicCamera,
    PanZoomController,
    PerspectiveCamera,
    TrackballController,
)
from tractome.mem import state_manager, visualization_manager


class CenterSectionWidget(QFrame):
    """Center section container for visualization/content."""

    def __init__(self):
        super().__init__()
        self.setObjectName("interactionCenterSection")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._3D_scene = window.Scene(background=(0.2, 0.2, 0.2))
        self._3D_camera = PerspectiveCamera()
        self._3D_camera.add(DirectionalLight())
        self._3D_scene.add(self._3D_camera)
        self._3D_controller = TrackballController(self._3D_camera)

        self._2D_scene = window.Scene(background=(0.2, 0.2, 0.2))
        self._2D_scene.add(DirectionalLight())
        self._2D_camera = OrthographicCamera()
        self._2D_controller = PanZoomController(self._2D_camera)

        self.show_manager = window.ShowManager(
            scene=self._3D_scene,
            camera=self._3D_camera,
            controller=self._3D_controller,
            qt_app=QApplication.instance(),
            window_type="qt",
        )

        self._3D_controller.register_events(self.show_manager.renderer)
        self._2D_controller.register_events(self.show_manager.renderer)
        self._2D_controller.enabled = False

        # TODO: Remove long press event handler for Qt
        # This is a temporary workaround for the long press issue in Qt
        self.show_manager.renderer.remove_event_handler(
            self.show_manager._set_key_long_press_event, "key_up", "key_down"
        )

        def _register_clicks(event):
            """Handle selection clicks.

            Parameters
            ----------
            event : Event
                The click event.
            """
            if event.type == "pointer_down":
                self._focused_actor = event.target
            elif event.type == "pointer_up" and self._focused_actor != event.target:
                self._focused_actor = None
            elif event.type == "pointer_up" and self._focused_actor == event.target:
                event = Event(
                    type="on_selection", target=self._focused_actor, bubbles=False
                )
                self.show_manager.renderer.dispatch_event(event)
                self._focused_actor = None
            else:
                self._focused_actor = None

        self.show_manager.renderer.add_event_handler(
            _register_clicks, "pointer_down", "pointer_up"
        )

        self.show_manager.renderer.add_event_handler(
            self.handle_key_strokes, "key_down"
        )

        viz_window = self.show_manager.window
        if not isinstance(viz_window, QWidget):
            viz_window = QWidget.createWindowContainer(viz_window, self)

        viz_window.setObjectName("interactionVizWindow")
        layout.addWidget(viz_window, 0, 0)

        self._build_display_info_overlay(layout)
        self._build_keystroke_card(layout)

    def _build_display_info_overlay(self, parent_layout):
        """Create display info overlay inside the visualization area."""
        self._display_info_widget = QFrame(self)
        self._display_info_widget.setObjectName("displayInfoWidget")
        self._display_info_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        info_layout = QVBoxLayout(self._display_info_widget)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(4)

        title = QLabel("Display info", self._display_info_widget)
        title.setObjectName("displayInfoTitle")
        info_layout.addWidget(title)

        self._display_cluster_count = QLabel(
            "# of clusters: 0", self._display_info_widget
        )
        self._display_roi_count = QLabel("# of ROI: 0", self._display_info_widget)
        self._display_fibers_count = QLabel("# of fibers: 0", self._display_info_widget)

        info_layout.addWidget(self._display_cluster_count)
        info_layout.addWidget(self._display_roi_count)
        info_layout.addWidget(self._display_fibers_count)

        parent_layout.addWidget(
            self._display_info_widget,
            0,
            0,
            alignment=Qt.AlignTop | Qt.AlignLeft,
        )
        self._display_info_widget.raise_()

    def _build_keystroke_card(self, parent_layout):
        """Build the keystroke card."""
        self._keystroke_card = QFrame(self)
        self._keystroke_card.setObjectName("keystrokeCard")
        self._keystroke_card.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        info_layout = QVBoxLayout(self._keystroke_card)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(4)

        title = QLabel("Key Strokes", self._keystroke_card)
        title.setObjectName("keystrokeTitle")
        info_layout.addWidget(title)

        shortcut_lines = [
            "a: Select All",
            "n: Select None",
            "i: Swap Selection",
            "d: Delete Selection",
            "e: Expand Selection",
            "c: Collapse Selection",
            "s: Show Selection",
            "h: Hide Selection",
            "x: Toggle this message",
        ]
        self._keystroke_content = QLabel(
            "\n".join(shortcut_lines), self._keystroke_card
        )
        self._keystroke_content.setObjectName("keystrokeContent")
        self._keystroke_content.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_layout.addWidget(self._keystroke_content)

        parent_layout.addWidget(
            self._keystroke_card,
            0,
            0,
            alignment=Qt.AlignBottom | Qt.AlignLeft,
        )
        self._keystroke_card.raise_()

    def add_visualization(self, visualizations, visualization_type="unknown"):
        """Add visualizations to the center section.

        Parameters
        ----------
        visualizations : list
            The visualizations to add.
        visualization_type : str, optional
            Type/category of the visualization payload.
        """
        self._3D_scene.add(*visualizations)
        if visualization_type == "tractogram":
            self._update_display_info()
            self._keystroke_card.setVisible(True)
        self._refresh_overlays()

    def remove_visualization(self, visualizations, *, visualization_type="unknown"):
        """Remove visualizations from the center section.

        Parameters
        ----------
        visualizations : list
            The visualizations to remove.
        """
        self._3D_scene.remove(*visualizations)
        if visualization_type == "tractogram":
            self._update_display_info()
            self._keystroke_card.setVisible(False)
        self._refresh_overlays()

    def add_2d_visualization(self, visualizations):
        """Add visualizations to the 2D scene.

        Parameters
        ----------
        visualizations : list
            The 2D actors to add.
        """
        if not visualizations:
            return
        self._2D_scene.add(*visualizations)

    def remove_2d_visualization(self, visualizations):
        """Remove visualizations from the 2D scene.

        Parameters
        ----------
        visualizations : list
            The 2D actors to remove.
        """
        if not visualizations:
            return
        self._2D_scene.remove(*visualizations)

    def set_view_mode(self, mode):
        """Swap the active scene/camera/controller for 3D or 2D mode.

        The renderer pipeline only commits the new scene on the frame
        after the swap, so a single ``render()`` call after switching
        leaves a stale image on the canvas. A deferred second render is
        scheduled via ``QTimer.singleShot`` to guarantee a fresh paint
        once Qt has processed the scene/camera reassignment.

        Parameters
        ----------
        mode : str
            Either ``"3D"`` or ``"2D"``.
        """
        screen = self.show_manager.screens[0]
        if mode == "2D":
            screen.scene = self._2D_scene
            screen.camera = self._2D_camera
            screen.controller = self._2D_controller
            self._3D_controller.enabled = False
            self._2D_controller.enabled = True
            t1_actor = self._2D_scene_t1_actor()
            if t1_actor is not None:
                self._2D_camera.show_object(
                    t1_actor,
                    tuple(
                        -1 * np.asarray(state_manager.t1_slice_visibility_2d, dtype=int)
                    ),
                )
        else:
            screen.scene = self._3D_scene
            screen.camera = self._3D_camera
            screen.controller = self._3D_controller
            self._3D_controller.enabled = True
            self._2D_controller.enabled = False
        self.show_manager.render()
        QTimer.singleShot(0, self.show_manager.render)
        self._refresh_overlays()

    def _2D_scene_t1_actor(self):
        """Return the T1 slicer currently in the 2D scene, or None."""
        t1_viz = visualization_manager.t1_2d_visualizations
        if not t1_viz:
            return None
        return t1_viz[0]

    def _refresh_overlays(self):
        """Force the Qt overlays to fully repaint after a scene update.

        The keystroke card sits over the wgpu canvas with a translucent
        background and its text never changes, so repeated scene frames
        otherwise leave antialiased ghosts on top of the static labels.
        Re-raising and updating the widgets clears the accumulated pixels.
        """
        for overlay in (self._display_info_widget, self._keystroke_card):
            overlay.raise_()
            overlay.update()

    def _update_display_info(self):
        """Update display info overlay for latest added visualization."""
        latest_state = state_manager.get_latest_state()

        cluster_count = latest_state.nb_clusters
        fibers_count = len(latest_state.streamline_ids)
        if latest_state.filtered_streamline_ids is not None:
            visible_ids = set(
                np.asarray(latest_state.streamline_ids, dtype=np.int64).tolist()
            )
            filtered_ids = set(
                np.asarray(
                    latest_state.filtered_streamline_ids, dtype=np.int64
                ).tolist()
            )
            roi_count = len(visible_ids & filtered_ids)
        else:
            roi_count = "N/A"

        self._display_cluster_count.setText(f"# of clusters: {cluster_count}")
        self._display_roi_count.setText(f"# of ROI: {roi_count}")
        self._display_fibers_count.setText(f"# of fibers: {fibers_count}")

    def handle_key_strokes(self, event):
        """Handle key strokes.

        Parameters
        ----------
        event : Event
            The key stroke event.
        """
        if event.key == "e":
            self.remove_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
            visualization_manager.expand_clusters()
            self.add_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
        elif event.key == "c":
            self.remove_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
            visualization_manager.collapse_clusters()
            self.add_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
        elif event.key == "h":
            visualization_manager.hide_clusters()
        elif event.key == "s":
            visualization_manager.show_clusters()
        elif event.key == "a":
            visualization_manager.select_all_clusters()
        elif event.key == "n":
            visualization_manager.select_none_clusters()
        elif event.key == "i":
            visualization_manager.swap_clusters()
        elif event.key == "d":
            self.remove_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
            visualization_manager.delete_clusters()
            self.add_visualization(
                visualization_manager.tractogram_visualizations,
                visualization_type="tractogram",
            )
        elif event.key == "x":
            self._keystroke_card.setVisible(not self._keystroke_card.isVisible())
