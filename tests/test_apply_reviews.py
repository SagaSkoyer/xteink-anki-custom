"""Replaying a device batch back into Anki.

Offline resurfacing means a card can be answered several times before the
device ever reaches Wi-Fi: once per day the whole pulled batch becomes due
again locally. Those answers are the point of the feature -- the add-on must
apply every one of them, in order, each at the moment it was actually given.
"""

import pathlib
import sys
import types
import unittest

REPO_ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_export_collect import addon_module  # noqa: E402  (installs the anki stubs)

PROTOCOL = addon_module.protocol if hasattr(addon_module, "protocol") else None
Review = addon_module.Review
PushBatch = addon_module.PushBatch


class FakeOpChanges:
    """Stands in for the protobuf message _apply_batch() accumulates into."""

    def __init__(self):
        self.merged = 0

    def MergeFrom(self, _other):  # noqa: N802 - protobuf spelling
        self.merged += 1


class FakeCard:
    def __init__(self, card_id):
        self.id = card_id
        self.timer_started = None

    def start_timer(self):
        self.timer_started = 0


class RecordingScheduler:
    """Records what build_answer/answer_card were handed, in call order."""

    def __init__(self, states_by_call=None):
        self.answers = []
        self.states_requested = []
        self._states_by_call = states_by_call or {}

    def build_answer(self, card, states, rating):
        return types.SimpleNamespace(
            card_id=card.id,
            rating=rating,
            states=states,
            answered_at_millis=None,
            milliseconds_taken=None,
        )

    def answer_card(self, answer):
        self.answers.append(answer)
        return FakeOpChanges()


class FakeBackend:
    def __init__(self, scheduler):
        self._scheduler = scheduler
        self._counter = 0

    def get_scheduling_states(self, card_id):
        # A distinct object per call, so the test can prove the states were
        # re-read between reviews rather than computed once and reused.
        self._counter += 1
        state = f"state-{card_id}-{self._counter}"
        self._scheduler.states_requested.append(state)
        return state


class FakeCollection:
    def __init__(self, scheduler):
        self.sched = scheduler
        self._backend = FakeBackend(scheduler)

    def get_card(self, card_id):
        return FakeCard(card_id)


class ApplyBatchTests(unittest.TestCase):
    def setUp(self):
        self._real_op_changes = addon_module.OpChanges
        addon_module.OpChanges = FakeOpChanges
        self.addCleanup(
            lambda: setattr(addon_module, "OpChanges", self._real_op_changes)
        )
        self.addon = addon_module.XteinkAddon.__new__(addon_module.XteinkAddon)

    def _batch(self, reviews):
        return PushBatch(
            batch_id="pull-1",
            reviews=tuple(reviews),
            flags=(),
            legacy_csv=False,
            derived_batch_id=False,
        )

    def test_repeated_reviews_of_one_card_all_apply_in_order(self):
        # Three days offline: the same card answered once per pass.
        scheduler = RecordingScheduler()
        collection = FakeCollection(scheduler)
        batch = self._batch(
            [
                Review(card_id=42, ease=3, answered_at_ms=1755000000000, duration_ms=100),
                Review(card_id=42, ease=1, answered_at_ms=1755086400000, duration_ms=200),
                Review(card_id=42, ease=3, answered_at_ms=1755172800000, duration_ms=300),
            ]
        )

        result = self.addon._apply_batch(collection, batch)

        self.assertEqual(result.processed, 3)
        self.assertEqual(result.rejected, [])
        self.assertEqual([a.rating for a in scheduler.answers], [3, 1, 3])
        self.assertEqual(
            [a.answered_at_millis for a in scheduler.answers],
            [1755000000000, 1755086400000, 1755172800000],
        )
        self.assertEqual(
            [a.milliseconds_taken for a in scheduler.answers], [100, 200, 300]
        )

    def test_scheduling_states_are_reread_between_reviews(self):
        # Review N+1 has to see the state review N produced, or the second
        # answer of a card is scheduled from stale state.
        scheduler = RecordingScheduler()
        collection = FakeCollection(scheduler)
        batch = self._batch(
            [
                Review(card_id=7, ease=3, answered_at_ms=1, duration_ms=1),
                Review(card_id=7, ease=3, answered_at_ms=2, duration_ms=1),
            ]
        )

        self.addon._apply_batch(collection, batch)

        states = [a.states for a in scheduler.answers]
        self.assertEqual(len(set(states)), 2, "states were reused between reviews")

    def test_unstamped_reviews_leave_answered_at_unset(self):
        # What a device with no usable RTC sends; Anki then applies at push time.
        scheduler = RecordingScheduler()
        collection = FakeCollection(scheduler)
        batch = self._batch([Review(card_id=9, ease=2, duration_ms=50)])

        self.addon._apply_batch(collection, batch)

        self.assertIsNone(scheduler.answers[0].answered_at_millis)

    def test_one_failing_review_does_not_drop_the_rest(self):
        scheduler = RecordingScheduler()
        collection = FakeCollection(scheduler)
        original_get_card = collection.get_card

        def flaky_get_card(card_id):
            if card_id == 2:
                raise RuntimeError("card was deleted on the desktop")
            return original_get_card(card_id)

        collection.get_card = flaky_get_card
        batch = self._batch(
            [
                Review(card_id=1, ease=3, duration_ms=1),
                Review(card_id=2, ease=3, duration_ms=1),
                Review(card_id=3, ease=3, duration_ms=1),
            ]
        )

        result = self.addon._apply_batch(collection, batch)

        self.assertEqual(result.processed, 2)
        self.assertEqual([r["card_id"] for r in result.rejected], ["2"])


if __name__ == "__main__":
    unittest.main()
