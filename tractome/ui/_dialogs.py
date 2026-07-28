"""Reusable modal dialogs for the tractome app."""

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)

from tractome.io import get_embedding_label


class EmbeddingSelectionDialog(QDialog):
    """Ask the user which embedding to use for clustering.

    Presented when a tractogram ships with more than one embedding. Each
    available embedding is offered as a radio button. The button text is the
    embedding's user-facing label (e.g. the stored key ``"dismatrix"`` is
    shown as ``"dissimilarity"``), while the value returned is the underlying
    stored key.
    """

    def __init__(self, embedding_names, parent=None):
        """Build the selection dialog.

        Parameters
        ----------
        embedding_names : list[str]
            Stored ``data_per_streamline`` keys of the embeddings available
            on the tractogram.
        parent : QWidget, optional
            The parent widget.
        """
        super().__init__(parent)
        self.setObjectName("embeddingSelectionDialog")
        self.setWindowTitle("Select embedding")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "This tractogram contains multiple embeddings.\n"
                "Choose which one to use for clustering:"
            )
        )

        self._button_group = QButtonGroup(self)
        for index, name in enumerate(embedding_names):
            radio = QRadioButton(get_embedding_label(name))
            if index == 0:
                radio.setChecked(True)
            self._button_group.addButton(radio, index)
            layout.addWidget(radio)

        self._embedding_names = list(embedding_names)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selected_embedding(self):
        """Return the embedding name chosen by the user.

        Returns
        -------
        str or None
            The selected embedding name, or None if nothing is selected.
        """
        checked_id = self._button_group.checkedId()
        if checked_id < 0:
            return None
        return self._embedding_names[checked_id]
