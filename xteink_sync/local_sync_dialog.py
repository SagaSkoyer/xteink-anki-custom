"""Tools > eInk (local): the SD-card-only sync workflow, no Wi-Fi pairing.

Export writes due cards into <parent>/system-due/ for the device's "Load
today's cards from SD" to pick up (AnkiStore::findNewestSdDueFile() in
AnkiStore.cpp). Import applies every <parent>/system-answers/*.ndjson file
the device wrote while you graded (AnkiStore::appendAnswerEvent()) back into
the real Anki collection. Both directions read/write the SD card's own
folders directly -- the folder you pick is wherever your computer mounts
the card itself, not a staging copy.

The actual card-collection/grading logic lives in XteinkAddon.export_due_to_
folder() / import_answers_from_folder() (__init__.py); this module is only
the Qt dialog around it.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, List

from aqt import mw
from aqt.qt import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showInfo

if TYPE_CHECKING:
    from . import XteinkAddon

LOGGER = logging.getLogger(__name__)


class LocalSyncDialog(QDialog):
    def __init__(self, addon: "XteinkAddon", translate) -> None:
        super().__init__(mw)
        self.addon = addon
        self._t = translate
        self.setWindowTitle(self._t("local_sync_title"))
        self.resize(420, 420)

        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)
        tabs.addTab(self._build_import_tab(), self._t("local_sync_import_tab"))
        tabs.addTab(self._build_export_tab(), self._t("local_sync_export_tab"))

    # -- Export tab ---------------------------------------------------

    def _build_export_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(self._t("local_sync_folder_label")))
        folder_row = QHBoxLayout()
        self.export_folder_edit = QLineEdit(tab)
        folder_row.addWidget(self.export_folder_edit)
        browse_button = QPushButton(self._t("local_sync_browse"), tab)
        browse_button.clicked.connect(
            lambda: self._browse_folder(self.export_folder_edit)
        )
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        layout.addWidget(QLabel(self._t("local_sync_deck_label")))
        self.deck_tree = QTreeWidget(tab)
        self.deck_tree.setHeaderHidden(True)
        self._populate_decks()
        self.deck_tree.itemChanged.connect(self._on_deck_item_changed)
        layout.addWidget(self.deck_tree)

        export_button = QPushButton(self._t("local_sync_export_button"), tab)
        export_button.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_button)

        return tab

    def _populate_decks(self) -> None:
        self.deck_tree.blockSignals(True)
        try:
            self.deck_tree.clear()
            if not self.addon.collection_ready():
                return
            try:
                entries = sorted(mw.col.decks.all_names_and_ids(), key=lambda e: e.name)
            except Exception:
                LOGGER.exception("Could not list decks for eInk local export")
                return

            # Group flat "Parent::Child" deck names into a tree so subdecks can
            # be collapsed/expanded under their parent via the branch chevron.
            nodes: dict = {}  # full path segments tuple -> QTreeWidgetItem
            for entry in entries:
                segments = tuple(entry.name.split("::"))
                parent_widget = self.deck_tree.invisibleRootItem()
                for depth in range(1, len(segments) + 1):
                    path = segments[:depth]
                    item = nodes.get(path)
                    if item is None:
                        item = QTreeWidgetItem(parent_widget, [path[-1]])
                        item.setFlags(
                            item.flags()
                            | Qt.ItemFlag.ItemIsUserCheckable
                            | Qt.ItemFlag.ItemIsAutoTristate
                        )
                        item.setCheckState(0, Qt.CheckState.Unchecked)
                        nodes[path] = item
                    parent_widget = item
                # The leaf item now corresponds to this actual Anki deck.
                nodes[segments].setData(0, Qt.ItemDataRole.UserRole, int(entry.id))

            self.deck_tree.expandAll()
        finally:
            self.deck_tree.blockSignals(False)

    def _on_deck_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        state = item.checkState(0)
        if state == Qt.CheckState.PartiallyChecked:
            return
        self.deck_tree.blockSignals(True)
        try:
            self._set_children_check_state(item, state)
        finally:
            self.deck_tree.blockSignals(False)

    def _set_children_check_state(
        self, item: QTreeWidgetItem, state: Qt.CheckState
    ) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_children_check_state(child, state)

    def _checked_deck_ids(self) -> List[int]:
        ids: List[int] = []

        def walk(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                child = item.child(i)
                if child.checkState(0) == Qt.CheckState.Checked:
                    deck_id = child.data(0, Qt.ItemDataRole.UserRole)
                    if deck_id is not None:
                        ids.append(int(deck_id))
                else:
                    walk(child)

        walk(self.deck_tree.invisibleRootItem())
        return ids

    def _on_export_clicked(self) -> None:
        parent_folder = self.export_folder_edit.text().strip()
        if not parent_folder:
            showInfo(self._t("local_sync_no_folder"))
            return
        deck_ids = self._checked_deck_ids()
        if not deck_ids:
            showInfo(self._t("local_sync_no_decks"))
            return
        if not self.addon.collection_ready():
            showInfo(self._t("local_sync_export_error", error="No Anki collection is open"))
            return

        def run_export() -> None:
            try:
                result = self.addon.export_due_to_folder(deck_ids, parent_folder)
            except Exception as error:
                LOGGER.exception("eInk local export failed")
                mw.taskman.run_on_main(
                    lambda: showInfo(self._t("local_sync_export_error", error=str(error)))
                )
                return

            def notify() -> None:
                if result["card_count"] == 0:
                    showInfo(self._t("local_sync_export_empty"))
                else:
                    showInfo(
                        self._t(
                            "local_sync_export_saved",
                            count=result["card_count"],
                            decks=result["deck_count"],
                            path=result["file_path"],
                        )
                    )

            mw.taskman.run_on_main(notify)

        # export_due_to_folder() blocks on a Future a main-thread QueryOp
        # resolves -- must run off the main thread the button click fired on.
        threading.Thread(target=run_export, daemon=True).start()

    # -- Import tab -----------------------------------------------------

    def _build_import_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(self._t("local_sync_folder_label")))
        folder_row = QHBoxLayout()
        self.import_folder_edit = QLineEdit(tab)
        folder_row.addWidget(self.import_folder_edit)
        browse_button = QPushButton(self._t("local_sync_browse"), tab)
        browse_button.clicked.connect(
            lambda: self._browse_folder(self.import_folder_edit)
        )
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        layout.addStretch(1)

        import_button = QPushButton(self._t("local_sync_import_button"), tab)
        import_button.clicked.connect(self._on_import_clicked)
        layout.addWidget(import_button)

        return tab

    def _on_import_clicked(self) -> None:
        parent_folder = self.import_folder_edit.text().strip()
        if not parent_folder:
            showInfo(self._t("local_sync_no_folder"))
            return
        if not self.addon.collection_ready():
            showInfo(self._t("local_sync_import_error", error="No Anki collection is open"))
            return

        def run_import() -> None:
            try:
                result = self.addon.import_answers_from_folder(parent_folder)
            except Exception as error:
                LOGGER.exception("eInk local import failed")
                mw.taskman.run_on_main(
                    lambda: showInfo(self._t("local_sync_import_error", error=str(error)))
                )
                return

            def notify() -> None:
                if result["files"] == 0 and result["skipped"] == 0:
                    showInfo(self._t("local_sync_import_empty"))
                    return
                message = self._t(
                    "local_sync_import_done",
                    processed=result["processed"],
                    files=result["files"],
                )
                if result["rejected"]:
                    message += self._t(
                        "local_sync_import_rejected", rejected=result["rejected"]
                    )
                if result["skipped"]:
                    message += self._t(
                        "local_sync_import_skipped", skipped=result["skipped"]
                    )
                showInfo(message)

            mw.taskman.run_on_main(notify)

        # import_answers_from_folder() -> apply_reviews() blocks on a Future a
        # main-thread CollectionOp resolves -- must run off the main thread.
        threading.Thread(target=run_import, daemon=True).start()

    # -- shared -----------------------------------------------------------

    def _browse_folder(self, target: QLineEdit) -> None:
        chosen = QFileDialog.getExistingDirectory(self, self._t("local_sync_folder_label"))
        if chosen:
            target.setText(chosen)


def open_local_sync_dialog(addon: "XteinkAddon") -> None:
    from . import _t  # local import: avoids a circular import at module load time

    dialog = LocalSyncDialog(addon, _t)
    dialog.exec()
