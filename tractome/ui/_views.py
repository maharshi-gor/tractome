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

from tractome.mem import visualization_manager
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

        main_layout.addWidget(self._left_section, 1)
        main_layout.addWidget(self._center_section, 3)
        main_layout.addWidget(self._right_section, 1)

    def _on_t1_changed(self):
        """Refresh T1 visualization after image upload/selection."""
        if visualization_manager.t1_visualizations:
            self.remove_visualization(
                visualization_manager.t1_visualizations, visualization_type="t1"
            )

        t1_visualization = visualization_manager.visualize_t1()
        if t1_visualization is not None:
            self.add_visualization(t1_visualization, visualization_type="t1")
        self._right_section.image_input_widget.sync_t1_visibility_button()

    def _on_t1_visibility_changed(self):
        """Re-render after toggling T1 visibility in the scene."""
        self._center_section.show_manager.render()

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
