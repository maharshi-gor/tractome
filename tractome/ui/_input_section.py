from PySide6.QtWidgets import QFrame, QVBoxLayout


class RightSectionWidget(QFrame):
    """Right section container for add-ons and track views."""

    def __init__(self):
        super().__init__()
        self.setObjectName("interactionRightSection")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addStretch()
