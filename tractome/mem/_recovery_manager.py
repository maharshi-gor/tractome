import logging

import numpy as np

from tractome.compute import stratified_subsample

FINE_LABELS_PREFIX = "fine_labels"


def fine_labels_key(embedding_name):
    """Return the ``data_per_streamline`` key caching strata for an embedding.

    Fine-stratum labels are produced by a MiniBatchKMeans pass over one
    specific embedding, so they are only meaningful alongside that embedding.
    Qualifying the key by embedding name keeps labels built from one embedding
    from being reused when another is selected.

    Parameters
    ----------
    embedding_name : str
        The ``data_per_streamline`` key of the embedding the labels describe.

    Returns
    -------
    str
        The cache key for that embedding's fine-stratum labels.
    """
    return f"{FINE_LABELS_PREFIX}__{embedding_name}"


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
    embedding_name : str or None
        Name of the embedding the current strata were built from.
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
        self.embedding_name = None

    def reset(self):
        """Clear all recovery state (called when the tractogram changes)."""
        self.__init__()

    def has_cached_labels(self, sft, embedding_name):
        """Report whether usable cached strata exist for ``embedding_name``.

        Used to decide up-front whether :meth:`build` will have to run the
        (slow) MiniBatchKMeans pass, so callers can show progress only when
        work is actually going to happen.

        Parameters
        ----------
        sft : StatefulTractogram
            The loaded tractogram.
        embedding_name : str
            The embedding whose cached strata are being looked for.

        Returns
        -------
        bool
            True when a valid cache is present and will be reused.
        """
        return self._read_cached_labels(sft, embedding_name) is not None

    def _read_cached_labels(self, sft, embedding_name):
        """Return validated cached strata for ``embedding_name``, else None.

        The cache lives in ``data_per_streamline``, which is arbitrary
        user-supplied data: an entry under the expected key may come from an
        unrelated pipeline. Labels are therefore only trusted when they are
        integral, non-negative, and bounded by the streamline count -- the
        assumptions :meth:`_subsample_from_labels` relies on. Anything else
        falls through to a fresh fine pass rather than silently steering it.

        Parameters
        ----------
        sft : StatefulTractogram
            The loaded tractogram.
        embedding_name : str
            The embedding whose cached strata are being read.

        Returns
        -------
        ndarray or None
            ``int32`` labels of shape ``(N,)``, or None when absent/unusable.
        """
        key = fine_labels_key(embedding_name)
        cached = sft.data_per_streamline.get(key, None)
        if cached is None:
            return None

        n = len(sft.streamlines)
        if n == 0:
            return None

        try:
            values = np.asarray(cached)
        except (ValueError, TypeError):
            logging.warning("Ignoring unreadable cached strata '%s'.", key)
            return None

        if values.size != n:
            logging.warning(
                "Ignoring cached strata '%s': %s values for %s streamlines.",
                key,
                values.size,
                n,
            )
            return None

        values = values.reshape(-1)
        if not np.issubdtype(values.dtype, np.number):
            logging.warning("Ignoring non-numeric cached strata '%s'.", key)
            return None
        if not np.all(np.isfinite(values)) or np.any(values != np.floor(values)):
            logging.warning("Ignoring non-integral cached strata '%s'.", key)
            return None

        labels = values.astype(np.int32)
        if labels.min() < 0 or labels.max() >= n:
            logging.warning(
                "Ignoring out-of-range cached strata '%s': ids span [%s, %s] "
                "for %s streamlines.",
                key,
                int(labels.min()),
                int(labels.max()),
                n,
            )
            return None

        return labels

    def build(self, sft, dismatrix, embedding_name):
        """Compute the working-set subsample and the recovery index.

        Runs once per tractogram. When the tractogram is at or below the
        subsampling threshold this is a no-op that returns every streamline id
        and leaves the manager inactive.

        Parameters
        ----------
        sft : StatefulTractogram
            The loaded tractogram; the fine-stratum labels are cached on its
            ``data_per_streamline`` under :func:`fine_labels_key` so they can
            persist with the tractogram and be reused without recomputation.
        dismatrix : ndarray
            The embedding of shape ``(N, num_prototypes)`` selected for
            clustering. Strata are built in this space, so the working set
            matches the space the clustering actually runs in.
        embedding_name : str
            Name of the embedding ``dismatrix`` was taken from. Qualifies the
            label cache so strata are never reused across embeddings.

        Returns
        -------
        ndarray
            ``int32`` streamline ids forming the interactive working set.
        """
        n = len(sft.streamlines)

        # Reuse cached labels (e.g. saved with the tractogram) when present.
        labels = self._read_cached_labels(sft, embedding_name)
        if labels is not None:
            result = self._subsample_from_labels(dismatrix, labels)
        else:
            result = stratified_subsample(dismatrix, seed=self.seed)

        sample_ids = np.asarray(result["sample_ids"], dtype=np.int32)
        self.labels = result["labels"]
        self.medoid_ids = result["medoid_ids"]
        self.k_s = result["k_s"]
        self.n = result["n"]
        self.active = self.labels is not None
        self.embedding_name = embedding_name

        if self.active:
            self.available_mask = np.ones(n, dtype=bool)
            self.available_mask[sample_ids] = False
            key = fine_labels_key(embedding_name)
            try:
                sft.data_per_streamline[key] = self.labels.reshape(-1, 1)
            except Exception as exc:  # pragma: no cover - defensive cache only
                logging.warning("Could not cache '%s' on tractogram: %s", key, exc)
        else:
            self.available_mask = None

        logging.info(
            "Recovery index built on '%s': N=%s, active=%s, k_s=%s, working set=%s",
            embedding_name,
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
            The selected embedding, used only to recover medoids.
        labels : ndarray
            Cached ``int32`` stratum id for every streamline, already
            validated by :meth:`_read_cached_labels`.

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
