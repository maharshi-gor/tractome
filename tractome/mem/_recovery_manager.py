import logging

import numpy as np

from tractome.compute import stratified_subsample


class RecoveryManager:
    """Manage the subsampled working set and the fiber-recovery index.

    A large tractogram is reduced to a stratified working set at load time (see
    :func:`tractome.compute.stratified_subsample`). This singleton keeps the
    per-streamline fine-stratum ``labels`` produced by that one-time pass so the
    un-sampled streamlines can be recovered on demand: siblings of a selection
    within a fine stratum are its embedding-space neighbours.

    State held here is *global per tractogram* (not per undo/redo state):

    labels : ndarray or None
        ``int32`` stratum id of every streamline in the full tractogram.
    medoid_ids : ndarray or None
        Medoid streamline id of each non-empty stratum.
    available_mask : ndarray or None
        Boolean mask over the full set: ``True`` where a streamline exists but
        is neither in the base sample nor already recovered. Cleared as ids are
        handed out; intentionally monotonic within a session.
    active : bool
        ``True`` only when subsampling actually happened (``N > threshold``).
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Return the singleton ``RecoveryManager`` instance."""
        if not cls._instance:
            cls._instance = super(RecoveryManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize (or reset) the recovery state to empty."""
        self.labels = None
        self.medoid_ids = None
        self.available_mask = None
        self.k_s = 0
        self.seed = 0
        self.n = 0
        self.active = False

    def reset(self):
        """Clear all recovery state (called when the tractogram changes)."""
        self.__init__()

    def build(self, sft, dismatrix):
        """Compute the working-set subsample and the recovery index.

        Runs once per tractogram. When the tractogram is at or below the
        subsampling threshold this is a no-op that returns every streamline id
        and leaves the manager inactive.

        Parameters
        ----------
        sft : StatefulTractogram
            The loaded tractogram; the fine-stratum labels are cached on its
            ``data_per_streamline["fine_labels"]`` so they can persist with the
            tractogram and be reused without recomputation.
        dismatrix : ndarray
            The dissimilarity embedding of shape ``(N, num_prototypes)``.

        Returns
        -------
        ndarray
            ``int32`` streamline ids forming the interactive working set.
        """
        n = len(sft.streamlines)

        # Reuse cached labels (e.g. saved with the tractogram) when present.
        cached = sft.data_per_streamline.get("fine_labels", None)
        if cached is not None and len(cached) == n:
            labels = np.asarray(cached, dtype=np.int32).reshape(-1)
            result = self._subsample_from_labels(dismatrix, labels)
        else:
            result = stratified_subsample(dismatrix, seed=self.seed)

        sample_ids = np.asarray(result["sample_ids"], dtype=np.int32)
        self.labels = result["labels"]
        self.medoid_ids = result["medoid_ids"]
        self.k_s = result["k_s"]
        self.n = result["n"]
        self.active = self.labels is not None

        if self.active:
            self.available_mask = np.ones(n, dtype=bool)
            self.available_mask[sample_ids] = False
            try:
                sft.data_per_streamline["fine_labels"] = self.labels.reshape(-1, 1)
            except Exception as exc:  # pragma: no cover - defensive cache only
                logging.warning("Could not cache fine_labels on tractogram: %s", exc)
        else:
            self.available_mask = None

        logging.info(
            "Recovery index built: N=%s, active=%s, k_s=%s, working set=%s",
            n,
            self.active,
            self.k_s,
            len(sample_ids),
        )
        return sample_ids

    def _subsample_from_labels(self, dismatrix, labels):
        """Rebuild a subsample from cached fine-stratum labels.

        Mirrors the allocation in :func:`stratified_subsample` but skips the
        MiniBatchKMeans pass, reusing labels already cached on the tractogram.

        Parameters
        ----------
        dismatrix : ndarray
            The dissimilarity embedding, used only to recover medoids.
        labels : ndarray
            Cached ``int32`` stratum id for every streamline.

        Returns
        -------
        dict
            Same shape as :func:`stratified_subsample`'s return value.
        """
        from tractome.compute import KEEP_FLOOR, SUBSAMPLE_THRESHOLD

        dismatrix = np.asarray(dismatrix, dtype=np.float32)
        n = labels.shape[0]
        pct = SUBSAMPLE_THRESHOLD / n
        rng = np.random.default_rng(self.seed)

        order = np.argsort(labels, kind="stable")
        sorted_labels = labels[order]
        n_clusters = int(labels.max()) + 1
        seg_starts = np.searchsorted(sorted_labels, np.arange(n_clusters), side="left")
        seg_ends = np.searchsorted(sorted_labels, np.arange(n_clusters), side="right")

        medoid_ids = []
        chosen = []
        for c in range(n_clusters):
            start, end = seg_starts[c], seg_ends[c]
            if start == end:
                continue
            members = order[start:end]
            diff = dismatrix[members] - dismatrix[members].mean(0)
            medoid = int(members[np.einsum("ij,ij->i", diff, diff).argmin()])
            medoid_ids.append(medoid)

            size = end - start
            keep = min(size, max(KEEP_FLOOR, int(round(pct * size))))
            chosen.append(np.asarray([medoid], dtype=members.dtype))
            remaining = members[members != medoid]
            extra = min(keep - 1, len(remaining))
            if extra > 0:
                chosen.append(rng.choice(remaining, extra, replace=False))

        return {
            "sample_ids": np.unique(np.concatenate(chosen)).astype(np.int32),
            "labels": labels,
            "medoid_ids": np.asarray(medoid_ids, dtype=np.int32),
            "k_s": n_clusters,
            "n": n,
        }


recovery_manager = RecoveryManager()
