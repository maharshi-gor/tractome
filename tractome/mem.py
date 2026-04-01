from dataclasses import dataclass

import numpy as np


class InputManager:
    """Manage input file paths and track the currently active items.

    This manager stores tractogram, T1, mesh, mesh texture, ROI, and parcel
    file paths while keeping the index of the currently selected item for each
    input type.
    """

    def __init__(self):
        """Manage input file paths and track the currently active items.

        This manager stores tractogram, T1, mesh, mesh texture, ROI, and
        parcel file paths while keeping the index of the currently selected
        item for each input type.
        """
        self._tractograms = []
        self._t1s = []
        self._meshes = []
        self._mesh_textures = []
        self._rois = []
        self._parcels = []

        self._current_tractogram = -1
        self._current_t1 = -1
        self._current_mesh = -1
        self._current_roi = -1
        self._current_parcel = -1

    def add_tractogram(self, tractogram):
        """Add a tractogram path and make it the current tractogram.

        Parameters
        ----------
        tractogram : str
            Path to the tractogram file to store.
        """
        self._tractograms.append(tractogram)
        self._current_tractogram = len(self._tractograms) - 1

    def add_t1(self, t1):
        """Add a T1 image path and make it the current T1 image.

        Parameters
        ----------
        t1 : str
            Path to the T1 image file to store.
        """
        self._t1s.append(t1)
        self._current_t1 = len(self._t1s) - 1

    def add_mesh(self, mesh, mesh_texture):
        """Add a mesh path and its texture path, and make them current.

        Parameters
        ----------
        mesh : str
            Path to the mesh file to store.
        mesh_texture : str
            Path to the texture file associated with ``mesh``.
        """
        self._meshes.append(mesh)
        self._mesh_textures.append(mesh_texture)
        self._current_mesh = len(self._meshes) - 1

    def add_roi(self, roi):
        """Add an ROI path and make it the current ROI.

        Parameters
        ----------
        roi : str
            Path to the ROI file to store.
        """
        self._rois.append(roi)
        self._current_roi = len(self._rois) - 1

    def add_parcel(self, parcel):
        """Add a parcel path and make it the current parcel.

        Parameters
        ----------
        parcel : str
            Path to the parcel file to store.
        """
        self._parcels.append(parcel)
        self._current_parcel = len(self._parcels) - 1

    def get_current_tractogram(self):
        """Return the current tractogram path.

        Returns
        -------
        str
            Path to the currently selected tractogram file.

        Raises
        ------
        ValueError
            If no tractogram is available.
        """
        if self._current_tractogram == -1:
            raise ValueError("No tractogram available.")
        return self._tractograms[self._current_tractogram]

    def get_current_t1(self):
        """Return the current T1 image path.

        Returns
        -------
        str
            Path to the currently selected T1 image file.

        Raises
        ------
        ValueError
            If no T1 image is available.
        """
        if self._current_t1 == -1:
            raise ValueError("No T1 image available.")
        return self._t1s[self._current_t1]

    def get_current_mesh(self):
        """Return the current mesh path.

        Returns
        -------
        str
            Path to the currently selected mesh file.

        Raises
        ------
        ValueError
            If no mesh is available.
        """
        if self._current_mesh == -1:
            raise ValueError("No mesh available.")
        return self._meshes[self._current_mesh]

    def get_current_roi(self):
        """Return the current ROI path.

        Returns
        -------
        str
            Path to the currently selected ROI file.

        Raises
        ------
        ValueError
            If no ROI is available.
        """
        if self._current_roi == -1:
            raise ValueError("No ROI available.")
        return self._rois[self._current_roi]

    def get_current_parcel(self):
        """Return the current parcel path.

        Returns
        -------
        str
            Path to the currently selected parcel file.

        Raises
        ------
        ValueError
            If no parcel is available.
        """
        if self._current_parcel == -1:
            raise ValueError("No parcel available.")
        return self._parcels[self._current_parcel]

    def has_input(self):
        """Check if any input is available.

        Returns
        -------
        bool
            True if at least one input type has at least one item, False
            otherwise.
        """
        return (
            len(self._tractograms) > 0
            or len(self._t1s) > 0
            or len(self._meshes) > 0
            or len(self._rois) > 0
            or len(self._parcels) > 0
        )


@dataclass
class ClusterState:
    """A class to represent the state of the application."""

    nb_clusters: int
    streamline_ids: np.ndarray
    max_clusters: int


class StateManager:
    """A class to manage the state of the application."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the StateManager if one does not exist."""
        if not cls._instance:
            cls._instance = super(StateManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, max_size=50):
        """Initialize the state manager.

        Parameters
        ----------
        max_size : int, optional
            The maximum number of states to keep in history.
        """
        self._states = []
        self._max_size = max_size
        self._current_index = -1  # -1 means no state yet

    def has_states(self):
        """Check if there are any states in the history.

        Returns
        -------
        bool
            True if there are states in the history, False otherwise.
        """
        return len(self._states) > 0

    def add_state(self, state):
        """Add a new state.

        Parameters
        ----------
        state : ClusterState
            The state to add.
        """
        if self._current_index < len(self._states) - 1:
            self._states = self._states[: self._current_index + 1]
        self._states.append(state)
        if len(self._states) > self._max_size:
            self._states = self._states[-self._max_size :]
        self._current_index = len(self._states) - 1

    def get_latest_state(self):
        """Get the current state (not always the last one).

        Returns
        -------
        ClusterState
            The current state.
        """
        if not self._states or self._current_index == -1:
            raise ValueError("No states available.")
        return self._states[self._current_index]

    def can_move_back(self):
        """Check if it's possible to move back to a previous state.

        Returns
        -------
        bool
            True if there are previous states to move back to, False otherwise.
        """
        return self._current_index > 0

    def move_back(self):
        """
        Move the pointer to the previous state (do not remove).

        Returns
        -------
        ClusterState
            The new current state after moving back.
        """
        if not self.can_move_back():
            raise ValueError("No previous state to move back to.")
        self._current_index -= 1
        return self.get_latest_state()

    def can_move_next(self):
        """Check if it's possible to move forward to a next state.

        Returns
        -------
        bool
            True if there is a next state to move forward to, False otherwise.
        """
        return self._current_index < len(self._states) - 1

    def move_next(self):
        """
        Move the pointer to the next state.

        Returns
        -------
        ClusterState
            The new current state after moving next.
        """
        if not self.can_move_next():
            raise ValueError("No next state to move forward to.")
        self._current_index += 1
        return self.get_latest_state()

    @property
    def history_size(self):
        """Get the number of states in the history.

        Returns
        -------
        int
            The number of states in the history.
        """
        return len(self._states)

    def get_all_states(self):
        """Get all states in history.

        Returns
        -------
        list
            A list of all states.
        """
        return list(self._states)

    def get_current_index(self):
        """Get the current index in the history.

        Returns
        -------
        int
            The current index.
        """
        return self._current_index
