from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
)

from tractome.mem import input_manager, state_manager, visualization_manager
from tractome.ui._paths import ICONS_PATH


class ClustersWidget(QFrame):
    """Refined, compact version of the Cluster controls."""

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("clustersWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        self.title = QLabel("CLUSTERS")
        self.title.setObjectName("clustersTitle")
        self.main_layout.addWidget(self.title)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(0, 0, 0, 0)

        std_h = 38

        self.count_input = QSpinBox()
        self.count_input.setObjectName("clusterCountInput")
        self.count_input.setRange(1, 100000)
        self.count_input.setValue(100)
        self.count_input.setButtonSymbols(QSpinBox.NoButtons)
        self.count_input.setFixedHeight(std_h)
        self.count_input.setMinimumWidth(56)
        self.count_input.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.count_input.returnPressed.connect(self._apply_clusters)
        self.grid.addWidget(self.count_input, 0, 0)

        step_layout = QVBoxLayout()
        step_layout.setSpacing(2)
        self.btn_up = QPushButton("")
        self.btn_down = QPushButton("")
        self.btn_up.setIcon(QIcon(str(ICONS_PATH / "arrow_up.svg")))
        self.btn_down.setIcon(QIcon(str(ICONS_PATH / "arrow_down.svg")))
        self.btn_up.setIconSize(QSize(12, 12))
        self.btn_down.setIconSize(QSize(12, 12))
        self.btn_up.setObjectName("clusterStepButton")
        self.btn_down.setObjectName("clusterStepButton")
        self.btn_up.setFixedSize(33, (std_h // 2) - 1)
        self.btn_down.setFixedSize(33, (std_h // 2) - 1)
        step_layout.addWidget(self.btn_up)
        step_layout.addWidget(self.btn_down)
        self.grid.addLayout(step_layout, 0, 1)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setObjectName("clusterApplyButton")
        self.btn_apply.setFixedHeight(std_h)
        self.btn_apply.setMinimumWidth(50)
        self.btn_apply.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_apply.clicked.connect(self._apply_clusters)
        self.grid.addWidget(self.btn_apply, 0, 2)

        self.btn_prev = QPushButton("Prev State")
        self.btn_next = QPushButton("Next State")
        self.btn_prev.setObjectName("clusterNavButton")
        self.btn_next.setObjectName("clusterNavButton")
        self.btn_prev.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.btn_next.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.btn_prev.setMinimumWidth(90)
        self.btn_next.setMinimumWidth(90)
        self.btn_prev.setFixedHeight(std_h)
        self.btn_next.setFixedHeight(std_h)
        self.btn_prev.clicked.connect(self._on_prev_state)
        self.btn_next.clicked.connect(self._on_next_state)

        self.grid.addWidget(self.btn_prev, 1, 0, 1, 2)
        self.grid.addWidget(self.btn_next, 1, 2)

        self.btn_settings = QToolButton()
        self.btn_settings.setObjectName("clusterSettingsButton")
        self.btn_settings.setFixedHeight(std_h)
        self.btn_settings.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.btn_settings.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btn_settings.setPopupMode(QToolButton.InstantPopup)
        settings_icon_path = ICONS_PATH / "settings.svg"
        if settings_icon_path.exists():
            self.btn_settings.setIcon(QIcon(str(settings_icon_path)))
            self.btn_settings.setIconSize(QSize(24, 24))

        self.settings_menu = QMenu(self.btn_settings)
        self.settings_menu.setObjectName("clusterSettingsMenu")
        self.settings_menu.aboutToShow.connect(self._sync_settings_menu_width)

        for action_label in (
            "All",
            "None",
            "Swap",
            "Show",
            "Hide",
            "Delete",
            "Expand",
            "Collapse",
        ):
            action = QAction(action_label, self.btn_settings)

            action.triggered.connect(
                lambda checked=False, label=action_label: self._on_cluster_menu_action(
                    label
                )
            )

            self.settings_menu.addAction(action)

        self.btn_settings.setMenu(self.settings_menu)
        self.grid.addWidget(self.btn_settings, 2, 0, 1, 3)

        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 0)
        self.grid.setColumnStretch(2, 1)

        self.main_layout.addLayout(self.grid)

        self.btn_up.clicked.connect(self.count_input.stepUp)
        self.btn_down.clicked.connect(self.count_input.stepDown)

        for btn in [
            self.btn_apply,
            self.btn_prev,
            self.btn_next,
            self.btn_settings,
            self.btn_up,
            self.btn_down,
        ]:
            btn.setCursor(Qt.PointingHandCursor)

    def _sync_settings_menu_width(self):
        """Keep settings dropdown width aligned to its button width."""
        self.settings_menu.setMinimumWidth(self.btn_settings.width())

    def _apply_clusters(self, *, only_cluster=True):
        """Apply the clusters."""
        value = self.count_input.value()
        if 1 <= value <= self.count_input.maximum():
            self._remove_tractogram_visualizations()
            if only_cluster:
                state_manager.get_latest_state().tractogram_states = None
            visualization_manager.visualize_tractogram(nb_clusters=value)
            self._add_tractogram_visualizations()

    def _remove_tractogram_visualizations(self):
        """Remove the tractogram visualizations."""
        parent = self.parent()
        parent.parent().remove_visualization(
            visualization_manager.tractogram_visualizations,
            visualization_type="tractogram",
        )

    def _add_tractogram_visualizations(self):
        """Add the tractogram visualizations."""
        parent = self.parent()
        parent.parent().add_visualization(
            visualization_manager.tractogram_visualizations,
            visualization_type="tractogram",
        )

    def _on_prev_state(self):
        """Handle the 'Previous State' button click."""
        if state_manager.can_move_back():
            latest_state = state_manager.move_back()
            self.count_input.setMaximum(latest_state.max_clusters)
            self.count_input.setValue(latest_state.nb_clusters)
            self._apply_clusters(only_cluster=False)

    def _on_next_state(self):
        """Handle the 'Next State' button click."""
        if state_manager.can_move_next():
            latest_state = state_manager.move_next()
            self.count_input.setMaximum(latest_state.max_clusters)
            self.count_input.setValue(latest_state.nb_clusters)
            self._apply_clusters(only_cluster=False)

    def _on_cluster_menu_action(self, action_name):
        """Handle cluster settings menu actions."""
        if action_name == "All":
            visualization_manager.select_all_clusters()
        elif action_name == "None":
            visualization_manager.select_none_clusters()
        elif action_name == "Swap":
            visualization_manager.swap_clusters()
        elif action_name == "Show":
            visualization_manager.show_clusters()
        elif action_name == "Hide":
            visualization_manager.hide_clusters()
        elif action_name == "Delete":
            self._remove_tractogram_visualizations()
            visualization_manager.delete_clusters()
            self._add_tractogram_visualizations()
        elif action_name == "Expand":
            self._remove_tractogram_visualizations()
            visualization_manager.expand_clusters()
            self._add_tractogram_visualizations()
        elif action_name == "Collapse":
            self._remove_tractogram_visualizations()
            visualization_manager.collapse_clusters()
            self._add_tractogram_visualizations()


class LeftSectionWidget(QFrame):
    """The Sidebar container that holds the control modules."""

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setObjectName("interactionLeftSection")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)

        self.clusters_box = ClustersWidget(parent=self)
        self.main_layout.addWidget(self.clusters_box)

        self.main_layout.addStretch()

    def update_controls_for_visualization(self):
        """Show/hide controls depending on visualization type."""
        has_tractogram_input = input_manager.has_tractogram
        self.clusters_box.setVisible(has_tractogram_input)

        if has_tractogram_input:
            self._sync_clusters_from_latest_state()

    def _sync_clusters_from_latest_state(self):
        """Populate cluster widget fields from your state manager."""
        if state_manager.has_states():
            state = state_manager.get_latest_state()
            self.clusters_box.count_input.setValue(int(state.nb_clusters))
