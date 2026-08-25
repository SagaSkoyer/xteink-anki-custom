"""SD-card import of a batch reviewed across several days.

The device writes one system-answers file per pass (AnkiStore's
currentAnswersFilePath()), because import_answers_from_folder() keys its
duplicate guard on the filename stem: reusing one name across days would make
every pass after the first import a silent no-op.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_export_collect import addon_module  # noqa: E402  (installs the anki stubs)


class RecordingAddon:
    """The real import_answers_from_folder(), with apply_reviews() captured."""

    def __init__(self):
        self.applied = []
        self.processed_batch_ids = []

    def claim_batch(self, batch_id):
        if batch_id in self.processed_batch_ids:
            return "duplicate"
        self.processed_batch_ids.append(batch_id)
        return "claimed"

    def release_batch(self, batch_id):
        if batch_id in self.processed_batch_ids:
            self.processed_batch_ids.remove(batch_id)

    def apply_reviews(self, batch):
        self.applied.append(batch)
        return addon_module.ApplyResult(
            processed=len(batch.reviews) + len(batch.flags),
            rejected=[],
            changes=None,
        )

    import_answers_from_folder = (
        addon_module.XteinkAddon.import_answers_from_folder
    )


def _write_pass(answers_dir, stem, card_ids, answered_at_ms):
    path = os.path.join(answers_dir, f"{stem}.ndjson")
    with open(path, "w", encoding="utf-8") as f:
        for card_id in card_ids:
            f.write(
                json.dumps(
                    {
                        "type": "review",
                        "card_id": str(card_id),
                        "ease": 3,
                        "duration_ms": 100,
                        "answered_at_ms": answered_at_ms,
                    }
                )
                + "\n"
            )
    return path


class ImportAnswersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.answers_dir = os.path.join(self.tmp.name, "system-answers")
        os.makedirs(self.answers_dir)
        self.addon = RecordingAddon()

    def test_every_pass_of_one_batch_is_applied(self):
        # Ten days offline: pass 0 keeps the bare batch id, later passes are
        # suffixed. All eleven files must be applied, not deduplicated away.
        _write_pass(self.answers_dir, "pull-abc", [1, 2], 1755000000000)
        for pass_index in range(1, 11):
            _write_pass(
                self.answers_dir,
                f"pull-abc-p{pass_index:02d}",
                [1, 2],
                1755000000000 + pass_index * 86_400_000,
            )

        summary = self.addon.import_answers_from_folder(self.tmp.name)

        self.assertEqual(summary["files"], 11)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(summary["processed"], 22)
        self.assertEqual(len(self.addon.applied), 11)

    def test_passes_are_applied_in_order(self):
        # Reviews of the same card must reach the scheduler oldest first, so
        # the zero-padded suffix has to sort correctly past pass 9.
        day = 86_400_000
        base = 1755000000000
        _write_pass(self.answers_dir, "pull-abc", [1], base)
        for pass_index in (1, 2, 10):
            _write_pass(
                self.answers_dir,
                f"pull-abc-p{pass_index:02d}",
                [1],
                base + pass_index * day,
            )

        self.addon.import_answers_from_folder(self.tmp.name)

        stamps = [b.reviews[0].answered_at_ms for b in self.addon.applied]
        self.assertEqual(stamps, sorted(stamps))
        self.assertEqual(
            stamps, [base, base + day, base + 2 * day, base + 10 * day]
        )

    def test_reimporting_the_same_pass_is_still_skipped(self):
        # The per-file duplicate guard must survive the pass suffix.
        _write_pass(self.answers_dir, "pull-abc-p01", [1], 1755000000000)
        self.addon.import_answers_from_folder(self.tmp.name)

        _write_pass(self.answers_dir, "pull-abc-p01", [1], 1755000000000)
        summary = self.addon.import_answers_from_folder(self.tmp.name)

        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["files"], 0)

    def test_applied_files_are_consumed(self):
        _write_pass(self.answers_dir, "pull-abc", [1], 1755000000000)
        _write_pass(self.answers_dir, "pull-abc-p01", [1], 1755086400000)

        self.addon.import_answers_from_folder(self.tmp.name)

        self.assertEqual(os.listdir(self.answers_dir), [])


if __name__ == "__main__":
    unittest.main()
