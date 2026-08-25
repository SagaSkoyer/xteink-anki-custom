#!/usr/bin/env python3
"""Model the device's offline review loop so its rules can be checked off-device.

Mirrors AnkiStore's queue handling (src/anki/AnkiStore.cpp in the prepared
firmware tree, shipped as custom-bin-builds/patches/crosspoint-1.6.0rc-anki.patch):
per-deck roster/queue/cursor, the Again and Hard-on-learning re-insertion gaps,
bury, undo, and the once-per-local-date rebuild that makes a pulled batch due
again. Run it to see what a multi-day offline session should look like, and to
diff the expected anki-state.json against one pulled off a real SD card.

    python3 scripts/simulate_anki_rollover.py

Exits non-zero if any modelled rule is violated.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

MAX_REVIEW_ROWS = 4000  # AnkiStore::MAX_REVIEW_ROWS

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4


@dataclass
class Deck:
    deck_id: str
    name: str
    roster: List[int] = field(default_factory=list)
    queue: List[int] = field(default_factory=list)
    cursor: int = 0
    baseline: int = 0
    completed: int = 0

    def remaining(self) -> int:
        return max(0, len(self.queue) - self.cursor)


@dataclass
class Undo:
    valid: bool = False
    deck_index: int = 0
    cursor: int = 0
    baseline: int = 0
    completed: int = 0
    review_count: int = 0
    queue: List[int] = field(default_factory=list)


class Store:
    """The subset of AnkiStore the resurfacing feature touches."""

    def __init__(self, batch_id: str, decks: Dict[str, List[int]], learning=()):
        self.batch_id = batch_id
        self.decks: List[Deck] = []
        self.learning = set(learning)
        for deck_id, cards in decks.items():
            self.decks.append(
                Deck(
                    deck_id=deck_id,
                    name=deck_id,
                    roster=list(cards),
                    queue=list(cards),
                    baseline=len(cards),
                )
            )
        self.card_count = sum(len(c) for c in decks.values())
        self.current_deck = 0
        self.pass_index = 0
        self.date_stamp = 0
        self.review_count = 0
        self.rollover_flag = False
        self.reviews: List[tuple] = []  # (card_id, ease, answered_at_ms)
        self.undo = Undo()

    # --- helpers -------------------------------------------------------
    def deck(self) -> Deck:
        return self.decks[self.current_deck]

    def current_card(self) -> Optional[int]:
        deck = self.deck()
        if deck.cursor >= len(deck.queue):
            return None
        return deck.queue[deck.cursor]

    def review_log_full(self) -> bool:
        return self.review_count >= MAX_REVIEW_ROWS

    # --- AnkiStore::recordReview ---------------------------------------
    def record_review(self, ease: int, answered_at_ms: int = 0) -> None:
        card = self.current_card()
        assert card is not None, "no card to grade"
        assert not self.review_log_full(), "review log is full"
        deck = self.deck()

        self.undo = Undo(
            valid=True,
            deck_index=self.current_deck,
            cursor=deck.cursor,
            baseline=deck.baseline,
            completed=deck.completed,
            review_count=self.review_count,
            queue=list(deck.queue),
        )

        self.reviews.append((card, ease, answered_at_ms))
        deck.cursor += 1
        self.review_count += 1

        requeue = ease == AGAIN or (ease == HARD and card in self.learning)
        if requeue:
            gap = 5 if ease == AGAIN else 10
            deck.queue.insert(min(len(deck.queue), deck.cursor + gap), card)
        else:
            if deck.baseline == 0:
                deck.baseline = len(deck.queue)
            if deck.completed < deck.baseline:
                deck.completed += 1

    # --- AnkiStore::buryCurrentCard ------------------------------------
    def bury(self) -> None:
        card = self.current_card()
        assert card is not None
        deck = self.deck()
        deck.queue.pop(deck.cursor)
        deck.roster = [c for c in deck.roster if c != card]
        self.undo = Undo()

    # --- AnkiStore::undoLastReview -------------------------------------
    def undo_last(self) -> bool:
        if not self.undo.valid:
            return False
        deck = self.decks[self.undo.deck_index]
        deck.queue = list(self.undo.queue)
        deck.cursor = self.undo.cursor
        deck.baseline = self.undo.baseline
        deck.completed = self.undo.completed
        self.review_count = self.undo.review_count
        self.current_deck = self.undo.deck_index
        self.reviews.pop()
        self.undo = Undo()
        return True

    # --- AnkiStore::applyDayRolloverIfDue ------------------------------
    def apply_day_rollover(self, today: int) -> bool:
        if not self.decks or self.card_count == 0:
            return False
        if today == 0:  # no trustworthy RTC
            return False
        if self.date_stamp == 0:
            self.date_stamp = today  # adopt, do not resurface
            return False
        if today <= self.date_stamp:
            return False
        if self.review_log_full():
            return False

        for deck in self.decks:
            deck.queue = list(deck.roster)
            deck.cursor = 0
            deck.baseline = len(deck.queue)
            deck.completed = 0
        self.date_stamp = today
        self.pass_index += 1
        self.undo = Undo()
        self.current_deck = 0
        for i, deck in enumerate(self.decks):
            if deck.remaining() > 0:
                self.current_deck = i
                break
        self.rollover_flag = True
        return True

    # --- AnkiStore::currentAnswersFilePath -----------------------------
    def answers_filename(self) -> str:
        if self.pass_index > 0:
            return f"{self.batch_id}-p{self.pass_index:02d}.ndjson"
        return f"{self.batch_id}.ndjson"

    # --- AnkiStore::saveSession ----------------------------------------
    def state_json(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "card_count": self.card_count,
            "review_count": self.review_count,
            "current_deck": self.current_deck,
            "pass_index": self.pass_index,
            "date_stamp": self.date_stamp,
            "decks": [
                {
                    "id": d.deck_id,
                    "name": d.name,
                    "cursor": d.cursor,
                    "baseline": d.baseline,
                    "completed": d.completed,
                    "queue": d.queue,
                }
                for d in self.decks
            ],
        }

    # --- AnkiStore::recordReview's CSV row -----------------------------
    def reviews_csv(self) -> str:
        rows = []
        for card_id, ease, at in self.reviews:
            rows.append(
                f"{card_id},{ease},{at},{100}\n" if at else f"{card_id},{ease},,{100}\n"
            )
        return "".join(rows)


FAILURES: List[str] = []


def check(label: str, condition: bool) -> None:
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        FAILURES.append(label)


def scenario_multi_day() -> Store:
    print("Two decks, five cards; grade some, bury one, then roll the date over")
    store = Store("pull-abc", {"greek": [0, 1, 2], "german": [3, 4]}, learning={1})

    store.apply_day_rollover(20260824)  # first check anchors the pass
    check("first check adopts the date without resurfacing", store.pass_index == 0)
    check("date adopted", store.date_stamp == 20260824)

    store.record_review(GOOD, 1_755_000_000_000)  # card 0
    store.record_review(AGAIN, 1_755_000_001_000)  # card 1 -> requeued
    check("Again re-inserts within the pass", store.deck().queue.count(1) == 2)
    check("Again does not advance progress", store.deck().completed == 1)

    store.bury()  # buries card 2
    check("bury drops the card from the roster", 2 not in store.decks[0].roster)
    check("bury leaves the other cards", store.decks[0].roster == [0, 1])

    check("same-day re-check does nothing", not store.apply_day_rollover(20260824))
    check("clock going backwards does nothing", not store.apply_day_rollover(20260101))
    check("an unusable RTC does nothing", not store.apply_day_rollover(0))

    reviews_before = len(store.reviews)
    check("the date moving on starts a pass", store.apply_day_rollover(20260825))
    check("pass index advanced", store.pass_index == 1)
    check("every deck is full again", [d.remaining() for d in store.decks] == [2, 2])
    check("greek is its roster, buried card excluded", store.decks[0].queue == [0, 1])
    check("cursor reset", all(d.cursor == 0 for d in store.decks))
    check("progress reset", all(d.completed == 0 for d in store.decks))
    check("baseline matches the new queue", all(d.baseline == len(d.queue) for d in store.decks))
    check("earlier reviews are kept", len(store.reviews) == reviews_before)
    check("undo cannot cross a pass", not store.undo.valid)
    check("rollover flag raised for the UI", store.rollover_flag)

    # Each pass needs its own answers file: the add-on's SD import keys its
    # duplicate guard on the filename stem.
    check("pass 1 gets its own answers file", store.answers_filename() == "pull-abc-p01.ndjson")
    check("pass 0 keeps the plain filename", Store("pull-abc", {"d": [0]}).answers_filename() == "pull-abc.ndjson")
    return store


def scenario_review_accumulation() -> None:
    print("\nOne card, three days: three reviews, each on its own day")
    store = Store("pull-x", {"d": [0]})
    store.apply_day_rollover(20260101)
    for day, (date, stamp) in enumerate(
        ((20260101, 1_755_000_000_000), (20260102, 1_755_086_400_000), (20260103, 1_755_172_800_000))
    ):
        if day:
            store.apply_day_rollover(date)
        store.record_review(GOOD, stamp)

    check("one review per pass is kept", len(store.reviews) == 3)
    check("all three are the same card", {r[0] for r in store.reviews} == {0})
    check("timestamps are distinct and ordered", [r[2] for r in store.reviews] == sorted(r[2] for r in store.reviews))
    check(
        "the CSV is what buildPushJson() parses",
        store.reviews_csv().splitlines()[0] == "0,3,1755000000000,100",
    )

    unstamped = Store("pull-y", {"d": [0]})
    unstamped.record_review(GOOD, 0)
    check(
        "an unsynced device leaves answered_at empty",
        unstamped.reviews_csv().strip() == "0,3,,100",
    )


def scenario_log_cap() -> None:
    print("\nThe review log fills up before a new pass can start")
    store = Store("pull-z", {"d": [0]})
    store.apply_day_rollover(20260101)
    store.review_count = MAX_REVIEW_ROWS
    check("a full log blocks the next pass", not store.apply_day_rollover(20260102))
    check("but the batch is untouched", store.pass_index == 0)


def main() -> int:
    store = scenario_multi_day()
    scenario_review_accumulation()
    scenario_log_cap()

    print("\nExpected anki-state.json after the rollover above:")
    print(json.dumps(store.state_json(), indent=2, sort_keys=True))

    if FAILURES:
        print(f"\n{len(FAILURES)} rule(s) violated:")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("\nAll modelled rules hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
