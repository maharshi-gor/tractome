from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

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

    def _update_display_info(self):
        """Update display info overlay for latest added visualization."""
        latest_state = state_manager.get_latest_state()

        cluster_count = latest_state.nb_clusters
        fibers_count = len(latest_state.streamline_ids)
        if latest_state.filtered_streamline_ids is not None:
            roi_count = len(latest_state.filtered_streamline_ids)
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
            # visualization_manager.delete_clusters()
            pass
        elif event.key == "r":
            # visualization_manager.reset_view()
            pass
        elif event.key == "x":
            # visualization_manager.toggle_suggestion()
            pass
