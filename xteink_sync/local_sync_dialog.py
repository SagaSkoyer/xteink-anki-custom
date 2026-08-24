"""Tools > eInk (local): the SD-card-only sync workflow, no Wi-Fi pairing.

Export writes due cards into <parent>/system-due/ for the device's "Load
today's cards from SD" to pick up (AnkiStore::findNewestSdDueFile() in
AnkiStore.cpp). Import applies every <parent>/system-answers/*.ndjson file
the device wrote while you graded (AnkiStore::appendAnswerEvent()) back into
the real Anki collection. Both directions read/write the SD card's own
folders directly -- "parent folder" is meant to be wherever your computer
mounts the card, not a staging copy.

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
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    Qt,
    QTabWidget,
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
        self.deck_list = QListWidget(tab)
        self.deck_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._populate_decks()
        layout.addWidget(self.deck_list)

        export_button = QPushButton(self._t("local_sync_export_button"), tab)
        export_button.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_button)

        return tab

    def _populate_decks(self) -> None:
        self.deck_list.clear()
        if not self.addon.collection_ready():
            return
        try:
            entries = sorted(mw.col.decks.all_names_and_ids(), key=lambda e: e.name)
        except Exception:
            LOGGER.exception("Could not list decks for eInk local export")
            return
        for entry in entries:
            item = QListWidgetItem(entry.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, int(entry.id))
            self.deck_list.addItem(item)

    def _checked_deck_ids(self) -> List[int]:
        ids: List[int] = []
        for i in range(self.deck_list.count()):
            item = self.deck_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(int(item.data(Qt.ItemDataRole.UserRole)))
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
