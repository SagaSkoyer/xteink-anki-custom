"""Deck-scoped export collection tests.

The add-on package imports Anki/Qt at module scope, so this installs light
stand-ins for the handful of names it touches, then drives the real
XteinkAddon._collect_due_cards() against a fake collection.
"""

import pathlib
import sys
import types
import unittest


REPO_ROOT = pathlib.Path(__file__).parents[1]


def _install_anki_stubs() -> None:
    if "anki" in sys.modules:
        return

    anki = types.ModuleType("anki")
    lang = types.ModuleType("anki.lang")
    lang.current_lang = "en"
    anki.lang = lang
    cards = types.ModuleType("anki.cards")

    class Card:  # noqa: D401 - stand-in for anki.cards.Card
        def __init__(self, col=None, backend_card=None):
            self.id = int(getattr(backend_card, "id", 0) or 0)

    cards.Card = Card
    collection_mod = types.ModuleType("anki.collection")
    collection_mod.OpChanges = object
    consts = types.ModuleType("anki.consts")
    consts.CARD_TYPE_NEW = 0
    consts.CARD_TYPE_LRN = 1
    consts.CARD_TYPE_REV = 2
    consts.CARD_TYPE_RELEARNING = 3
    scheduler = types.ModuleType("anki.scheduler")
    v3 = types.ModuleType("anki.scheduler.v3")

    class CardAnswer:
        AGAIN = 1
        HARD = 2
        GOOD = 3
        EASY = 4

    v3.CardAnswer = CardAnswer
    anki.cards = cards
    anki.collection = collection_mod
    anki.consts = consts
    anki.scheduler = scheduler
    scheduler.v3 = v3

    aqt = types.ModuleType("aqt")

    class _Hook(list):
        pass

    gui_hooks = types.SimpleNamespace(
        main_window_did_init=_Hook(), profile_will_close=_Hook()
    )

    class _AddonManager:
        def getConfig(self, _name):
            return {"api_token": "x" * 32}

        def writeConfig(self, _name, _config):
            return None

    class _Menu:
        def addAction(self, _action):
            return None

    mw = types.SimpleNamespace(
        addonManager=_AddonManager(),
        form=types.SimpleNamespace(menuTools=_Menu()),
        col=None,
        taskman=types.SimpleNamespace(run_on_main=lambda fn: fn()),
    )
    aqt.gui_hooks = gui_hooks
    aqt.mw = mw
    operations = types.ModuleType("aqt.operations")
    operations.CollectionOp = object
    operations.QueryOp = object
    qt = types.ModuleType("aqt.qt")

    class QAction:
        def __init__(self, *_args, **_kwargs):
            self.triggered = None

    class QTimer:
        pass

    qt.QAction = QAction
    qt.QTimer = QTimer
    qt.qconnect = lambda *_args, **_kwargs: None

    def _qt_placeholder(name):
        # local_sync_dialog imports a pile of widget classes at module scope;
        # none of them are constructed by these tests.
        return type(name, (), {"__getattr__": lambda self, _item: None})

    qt.__getattr__ = _qt_placeholder
    utils = types.ModuleType("aqt.utils")
    utils.showInfo = lambda *_args, **_kwargs: None
    aqt.operations = operations
    aqt.qt = qt
    aqt.utils = utils

    for name, module in (
        ("anki", anki),
        ("anki.lang", lang),
        ("anki.cards", cards),
        ("anki.collection", collection_mod),
        ("anki.consts", consts),
        ("anki.scheduler", scheduler),
        ("anki.scheduler.v3", v3),
        ("aqt", aqt),
        ("aqt.operations", operations),
        ("aqt.qt", qt),
        ("aqt.utils", utils),
    ):
        sys.modules[name] = module


_install_anki_stubs()
sys.path.insert(0, str(REPO_ROOT))
import xteink_sync as addon_module  # noqa: E402


class FakeCard:
    def __init__(self, card_id, deck_id, card_type, due, text, odid=0):
        self.id = card_id
        self.did = deck_id
        self.odid = odid
        self.type = card_type
        self.queue = card_type
        self.due = due
        self.reps = 0
        self.mod = 1_700_000_000
        self.flags = 0
        self.ord = 0
        self._text = text

    def question(self):
        return f"Q {self._text}"

    def answer(self):
        return f"Q {self._text}<hr id=answer>A {self._text}"

    def note(self):
        return types.SimpleNamespace(
            fields=[f"Q {self._text}", f"A {self._text}"],
            note_type=lambda: {
                "flds": [{"name": "Front"}, {"name": "Back"}],
                "tmpls": [{"name": "Card 1"}],
                "name": "Basic",
            },
        )


class FakeDecks:
    def __init__(self, names):
        self._names = names
        self._current = next(iter(names))

    def get_current_id(self):
        return self._current

    def select(self, deck_id):
        self._current = deck_id

    def name(self, deck_id):
        return self._names[int(deck_id)]

    def all_names_and_ids(self):
        return [
            types.SimpleNamespace(id=deck_id, name=name)
            for deck_id, name in self._names.items()
        ]


class FakeDb:
    def __init__(self, cards):
        self._cards = cards

    def all(self, sql):
        ids = sql.split("(")[-1].split(")")[0].split(",")
        wanted = {int(value) for value in ids if value.strip()}
        return [(c.id, c.due) for c in self._cards if c.id in wanted]


class FakeScheduler:
    def __init__(self, queued_by_deck, decks, tree):
        self._queued_by_deck = queued_by_deck
        self._decks = decks
        self._tree = tree

    def deck_due_tree(self):
        return self._tree

    def get_queued_cards(self, fetch_limit=1):
        current = self._decks.get_current_id()
        queued = self._queued_by_deck.get(current, [])[:fetch_limit]
        return types.SimpleNamespace(
            cards=[types.SimpleNamespace(card=c) for c in queued]
        )


class FakeCollection:
    def __init__(self, names, cards, queued_by_deck, tree):
        self.decks = FakeDecks(names)
        self._cards = {c.id: c for c in cards}
        self.db = FakeDb(cards)
        self.sched = FakeScheduler(queued_by_deck, self.decks, tree)

    def get_card(self, card_id):
        return self._cards[int(card_id)]

    def find_cards(self, query):
        # Only the shapes _deck_study_card_ids() builds are understood here.
        deck_name = query.split('"deck:', 1)[1].split('"', 1)[0].replace("\\", "")
        deck_id = next(
            deck_id
            for deck_id, name in self.decks._names.items()
            if name == deck_name
        )
        wants_new = "is:new" in query
        wants_review = "is:review -is:learn" in query
        found = []
        for card in self._cards.values():
            if int(card.odid or card.did) != deck_id:
                continue
            if wants_new and card.type == 0:
                found.append(card.id)
            elif wants_review and card.type == 2:
                found.append(card.id)
        return found


def _node(deck_id, name, new=0, learn=0, review=0, children=()):
    return types.SimpleNamespace(
        deck_id=deck_id,
        name=name,
        new_count=new,
        learn_count=learn,
        review_count=review,
        children=list(children),
    )


class CollectDueCardsTests(unittest.TestCase):
    def _addon(self):
        instance = addon_module.XteinkAddon.__new__(addon_module.XteinkAddon)
        instance.config = dict(addon_module.DEFAULT_CONFIG)
        return instance

    def test_scoped_export_includes_new_cards_when_queue_is_empty(self):
        """A deck of 100 new cards exports even with its daily limit used up."""

        names = {1: "News", 2: "Other"}
        cards = [FakeCard(1000 + i, 1, 0, i, f"news {i}") for i in range(100)]
        cards += [FakeCard(2000 + i, 2, 2, i, f"other {i}") for i in range(50)]
        # Nothing is due today anywhere: empty queues and a zeroed due tree.
        tree = _node(0, "", children=[_node(1, "News"), _node(2, "Other")])
        col = FakeCollection(names, cards, {}, tree)

        payload, decks = self._addon()._collect_due_cards(col, (200, 200), {1})

        self.assertEqual(len(payload), 100)
        self.assertEqual([d["name"] for d in decks], ["News"])
        self.assertTrue(all(c["deck_id"] == "1" for c in payload))
        self.assertTrue(all(c["card_type"] == "new" for c in payload))
        # Study order: sorted by the scheduler's due value (new-card position).
        self.assertEqual(payload[0]["id"], "1000")
        self.assertEqual(payload[-1]["id"], "1099")

    def test_scope_budget_is_not_spent_on_other_decks(self):
        names = {1: "News", 2: "Other"}
        cards = [FakeCard(1000 + i, 1, 0, i, f"news {i}") for i in range(10)]
        cards += [FakeCard(2000 + i, 2, 2, i, f"other {i}") for i in range(10)]
        tree = _node(
            0,
            "",
            new=10,
            review=10,
            children=[_node(1, "News", new=10), _node(2, "Other", review=10)],
        )
        queued = {2: [c for c in cards if c.did == 2]}
        col = FakeCollection(names, cards, queued, tree)

        payload, decks = self._addon()._collect_due_cards(col, (5, 5), {1})

        self.assertEqual(len(payload), 5)
        self.assertEqual({c["deck_id"] for c in payload}, {"1"})

    def test_study_order_new_then_review(self):
        names = {1: "Mixed"}
        cards = [FakeCard(1000 + i, 1, 2, i, f"rev {i}") for i in range(3)]
        cards += [FakeCard(2000 + i, 1, 0, i, f"new {i}") for i in range(3)]
        tree = _node(0, "", children=[_node(1, "Mixed")])
        col = FakeCollection(names, cards, {}, tree)

        payload, _decks = self._addon()._collect_due_cards(col, (10, 10), {1})

        self.assertEqual(
            [c["card_type"] for c in payload],
            ["new", "new", "new", "review", "review", "review"],
        )

    def test_unscoped_collection_is_unchanged(self):
        names = {1: "News", 2: "Other"}
        cards = [FakeCard(1000 + i, 1, 0, i, f"news {i}") for i in range(3)]
        tree = _node(0, "", new=3, children=[_node(1, "News", new=3)])
        col = FakeCollection(names, cards, {1: cards}, tree)

        payload, decks = self._addon()._collect_due_cards(col, (10, 10))

        self.assertEqual(len(payload), 3)
        self.assertEqual([d["name"] for d in decks], ["News"])

    def test_filtered_deck_card_is_filed_under_its_home_deck(self):
        names = {1: "News", 3: "Filtered"}
        card = FakeCard(1000, 3, 2, 0, "borrowed", odid=1)
        tree = _node(0, "", review=1, children=[_node(3, "Filtered", review=1)])
        col = FakeCollection(names, [card], {3: [card]}, tree)

        payload, decks = self._addon()._collect_due_cards(col, (10, 10), {1, 3})

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["deck_id"], "1")
        self.assertEqual([d["name"] for d in decks], ["News"])


if __name__ == "__main__":
    unittest.main()
