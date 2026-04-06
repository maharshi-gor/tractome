from tractome.mem import input_manager
from tractome.viz import create_image_slicer


class VisualizationManager:
    """A class to manage the visualization of the inputs."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the VisualizationManager if one does not exist.

        Parameters
        ----------
        *args : tuple
            Variable length argument list.
        **kwargs : dict
            Arbitrary keyword arguments.

        Returns
        -------
        VisualizationManager
            The instance of the VisualizationManager.
        """
        if not cls._instance:
            cls._instance = super(VisualizationManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._visualizations = {
            "tractogram": None,
            "t1": None,
            "mesh": None,
            "roi": None,
            "parcel": None,
        }

    def visualize_t1(self):
        """Visualize the T1 image.

        Returns
        -------
        Group
            The visualized T1 image with X, Y, and Z slices.
        """
        img, affine, _, _ = input_manager.get_current_t1()
        if img is not None:
            self._visualizations["t1"] = create_image_slicer(img, affine=affine)
        return self._visualizations["t1"]


visualization_manager = VisualizationManager()
