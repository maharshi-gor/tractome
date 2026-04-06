import os

from dipy.tracking.distances import bundles_distances_mam
import numpy as np

from fury import distinguishable_colormap
from tractome.compute import compute_dissimilarity, mkbm_clustering
from tractome.mem import ClusterState, input_manager, state_manager
from tractome.viz import create_image_slicer, create_streamlines, create_streamtube


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
        if not input_manager.has_t1:
            return None

        img, affine, _, _ = input_manager.get_current_t1()
        self._visualizations["t1"] = [create_image_slicer(img, affine=affine)]
        return self._visualizations["t1"]

    def visualize_tractogram(self, *, nb_clusters=100):
        """Visualize the tractogram.

        Parameters
        ----------
        nb_clusters : int, optional
            The number of clusters to create.

        Returns
        -------
        list
            The actors representing the tractogram.
        """

        if not input_manager.has_tractogram:
            return None

        sft, _, _, _ = input_manager.get_current_tractogram()
        is_embeddings_present = sft.data_per_streamline.get("dismatrix") is not None
        if not is_embeddings_present:
            n_jobs = max(1, (os.cpu_count() or 1) - 2)
            data_dissimilarity = compute_dissimilarity(
                np.asarray(sft.streamlines, dtype=object),
                distance=bundles_distances_mam,
                prototype_policy="sff",
                num_prototypes=40,
                verbose=False,
                size_limit=5000000,
                n_jobs=n_jobs,
            )
            sft.data_per_streamline["dismatrix"] = data_dissimilarity

        if not state_manager.has_states():
            state_manager.add_state(
                ClusterState(nb_clusters, np.arange(len(sft.streamlines)), 1000)
            )
        else:
            state_manager.get_latest_state().nb_clusters = nb_clusters

        self._apply_tractogram_states()

        actors = []
        for state_data in state_manager.get_latest_state().tractogram_states.values():
            if state_data["expanded"] is not True:
                actors.append(state_data["rep_actor"])
            else:
                actors.append(state_data["lines_actor"])
        self._visualizations["tractogram"] = actors
        return self._visualizations["tractogram"]

    def _apply_tractogram_states(self):
        """Apply the tractogram states to the visualization."""
        sft, _, _, _ = input_manager.get_current_tractogram()
        latest_state = state_manager.get_latest_state()
        if latest_state.tractogram_states is not None:
            for cluster_id, state_data in latest_state.tractogram_states.items():
                if state_data["expanded"] is not True:
                    state_data["rep_actor"] = create_streamtube(
                        sft.streamlines[cluster_id],
                        state_data["color"],
                        state_data["radius"],
                    )
                else:
                    state_data["lines_actor"] = create_streamlines(
                        sft.streamlines[state_data["streamline_ids"]],
                        state_data["color"],
                    )
        else:
            self._perform_clustering(sft, latest_state)

    def _perform_clustering(self, sft, state):
        """Perform clustering on the tractogram.

        Parameters
        ----------
        sft : StatefulTractogram
            The tractogram to cluster.
        state : ClusterState
            The state to perform clustering on.
        """
        colormap = distinguishable_colormap()
        streamline_ids = state.streamline_ids
        clusters = mkbm_clustering(
            sft.data_per_streamline["dismatrix"],
            n_clusters=state.nb_clusters,
            streamline_ids=streamline_ids,
        )
        min_size = min(len(streamline_ids) for streamline_ids in clusters.values())
        max_size = max(len(streamline_ids) for streamline_ids in clusters.values())
        size_range = max_size - min_size if max_size > min_size else 1
        state.tractogram_states = {}
        for cluster_id, streamline_ids in clusters.items():
            num_streamlines = len(streamline_ids)
            scaled_radius = ((num_streamlines - min_size) / size_range) * 2.0
            radius = max(scaled_radius, 1)
            state.tractogram_states[cluster_id] = {
                "streamline_ids": streamline_ids,
                "color": next(colormap),
                "selected": False,
                "expanded": False,
                "rep_actor": None,
                "lines_actor": None,
                "radius": radius,
            }
            state.tractogram_states[cluster_id]["rep_actor"] = create_streamtube(
                sft.streamlines[cluster_id],
                state.tractogram_states[cluster_id]["color"],
                state.tractogram_states[cluster_id]["radius"],
            )


visualization_manager = VisualizationManager()
