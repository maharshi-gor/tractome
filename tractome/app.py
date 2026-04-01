import logging
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from tractome.io import get_file_extension
from tractome.mem import InputManager
from tractome.ui import StartScreen, load_style_sheet

app = QApplication.instance() or QApplication([])


class Tractome(QMainWindow):
    """Tractome is a tool for analyzing and visualizing brain tractography data.

    It provides a pipeline for processing tractograms, meshes, and other related data,
    as well as a command-line interface for running the
    pipeline and computing dissimilarity matrices."""

    def __init__(
        self,
        tractogram=None,
        t1=None,
        mesh=None,
        mesh_texture=None,
        roi=None,
        parcel=None,
    ):
        """Initialize the Tractome pipeline.

        Parameters
        ----------
        tractogram : str, optional
            Path to the tractogram file
        t1 : str, optional
            Path to the T1-weighted image file
        mesh : str, optional
            Path to the mesh file
        mesh_texture : str, optional
            Path to the mesh texture file
        roi : list[str], optional
            List of paths to ROI files
        parcel : str, optional
            Path to a parcel CSV file
        """
        super().__init__()
        self._input_manager = InputManager()
        self._initialize_input_manager(tractogram, t1, mesh, mesh_texture, roi, parcel)
        self._initialize_window()

    def _initialize_input_manager(
        self, tractogram, t1, mesh, mesh_texture, roi, parcel
    ):
        """Initialize the input manager with pre-load files.

        Parameters
        ----------
        tractogram : str
            Path of tractogram.
        t1 : str
            Path of T1 image.
        mesh : str
            Path of surface mesh.
        mesh_texture : str
            Path of image texture for the mesh.
        roi : str
            Path of roi to showcase.
        parcel : str
            Path of parcel to showcase.
        """
        if tractogram is not None:
            self._input_manager.add_tractogram(tractogram)
        if t1 is not None:
            self._input_manager.add_t1(t1)
        if mesh is not None and mesh_texture is not None:
            self._input_manager.add_mesh(mesh, mesh_texture)
        if roi is not None:
            for roi_path in roi:
                self._input_manager.add_roi(roi_path)
        if parcel is not None:
            self._input_manager.add_parcel(parcel)

    def _completed_start_screen(self, file_path):
        """Handle the completion of the start screen."""
        self._file_uploaded(file_path)
        logging.info("File uploaded, switching to main screen.")
        # self._stack.setCurrentIndex(1)

    def _file_uploaded(self, file_path):
        """Handle the file uploaded event.

        Parameters
        ----------
        file_path : str
            Path of the uploaded file.
        """

        ext = get_file_extension(file_path)

        if ext in (".trx", ".trk"):
            self._input_manager.add_tractogram(file_path)

    def _initialize_window(self):
        """Initialize the window"""
        self.setWindowTitle("Tractome")
        self.resize(1200, 800)
        style_sheet = load_style_sheet()
        self.setStyleSheet(style_sheet)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        if not self._input_manager.has_input():
            self._start_screen = StartScreen(on_uploading_done=self._file_uploaded)
            self._stack.addWidget(self._start_screen)


if __name__ == "__main__":
    tractome = Tractome()
    tractome.show()
    sys.exit(app.exec())
