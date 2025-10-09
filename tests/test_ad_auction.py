import math
from typing import List
import pytest
import random
from sim.ad_auction import Bidder, AdSpot, Platform


# ---------- Fixtures and helpers ----------

def simple_valuation(bidder: Bidder, adspot: AdSpot, ctrs: List[float]) -> float:
    """Simple valuation: sum of bidder's tag weights matching adspot tags."""
    return sum(bidder.targeting.get(tag, 0.0) * ctr for tag, ctr in zip(adspot.tags, ctrs))


@pytest.fixture(autouse=True)
def fix_random_seed():
    """Fix random seed for deterministic sorting."""
    random.seed(0)
    yield
    random.seed(0)


# ---------- Bidder tests ----------

def test_bidder_default_and_custom_func():
    """Test truthful and custom bidding behaviors."""
    b = Bidder("A", {"sports": 1.0})
    a = AdSpot(1, ["sports"])
    assert b.name == "A"
    assert b.targeting == {"sports": 1.0}

    # default truthful bid == valuation
    val = b.valuation(a, simple_valuation, a.pos)
    assert val == 1.0
    assert b.bid(a, val) == 1.0

    # custom bid function multiplies valuation
    custom = Bidder("B", {"sports": 1.0},
                    bid_func=lambda bidder, adspot, v: v * 2)
    assert custom.bid(a, 1.0) == 2.0
    assert "Bidder(B)" in repr(custom)


# ---------- AdSpot initialization ----------

def test_adspot_init_default_and_explicit_ctrs():
    """Test creation with default and explicit CTRs."""
    a = AdSpot(2, ["a", "b"])
    assert a.num_slots == 2
    assert a.pos == [1.0, 1.0]
    assert a.tags == ["a", "b"]

    # explicit CTRs
    b = AdSpot(2, ["x"], pos=[0.8, 0.3])
    assert b.pos == [0.8, 0.3]

    # mismatched CTR length
    with pytest.raises(ValueError):
        AdSpot(2, ["a"], pos=[0.5])

    # invalid num_spots
    with pytest.raises(AssertionError):
        AdSpot(0, ["a"])


# ---------- assign(): valuation_fn errors ----------

def test_assign_raises_on_missing_valuation_fn():
    """Valuation function must be provided."""
    a = AdSpot(1, ["a"])
    with pytest.raises(ValueError):
        a.assign([], method="second_price", valuation_fn=None)


def test_assign_raises_on_unknown_method():
    """Auction method must be one of the known ones."""
    a = AdSpot(1, ["a"])
    b = Bidder("X", {"a": 1.0})
    with pytest.raises(ValueError):
        a.assign([b], method="not_a_method", valuation_fn=simple_valuation)


# ---------- Empty and filtering behaviors ----------

def test_assign_returns_empty_when_no_eligible_bidders():
    """If all valuations <= 0, return empty allocation."""
    a = AdSpot(2, ["a"])
    b = Bidder("X", {"b": 1.0})  # unrelated tag → valuation 0
    res = a.assign([b], method="first_price", valuation_fn=simple_valuation)
    assert res == {"winners": [None, None], "prices": [0.0, 0.0]}


# ---------- Auction logic tests ----------

def test_first_price_allocation_and_pricing():
    """Verify first-price auction pays own bid."""
    a = AdSpot(1, ["t"])
    b1 = Bidder("A", {"t": 3.0})
    b2 = Bidder("B", {"t": 2.0})
    res = a.assign([b1, b2], method="first_price", valuation_fn=simple_valuation)
    assert res["winners"][0] == b1
    assert math.isclose(res["prices"][0], 3.0)


def test_second_price_two_spots_pricing_rules():
    """Top bidders pay the next-highest bid in second-price auction."""
    a = AdSpot(2, ["sports"])
    b1 = Bidder("A", {"sports": 5.0})
    b2 = Bidder("B", {"sports": 3.0})
    b3 = Bidder("C", {"sports": 1.0})
    res = a.assign([b1, b2, b3], method="second_price", valuation_fn=simple_valuation)

    winners, prices = res["winners"], res["prices"]
    assert winners[0] == b1
    assert winners[1] == b2
    # Highest winner pays next-highest bid
    assert prices[0] == 3.0
    # Second winner pays next bid or 0
    assert prices[1] == 1.0


def test_second_price_with_fewer_bidders_than_slots():
    """Edge case: fewer eligible bidders than available slots."""
    a = AdSpot(3, ["a"])
    b1 = Bidder("A", {"a": 2.0})
    res = a.assign([b1], method="second_price", valuation_fn=simple_valuation)
    winners, prices = res["winners"], res["prices"]
    assert winners[0] == b1
    assert winners[1] is None
    assert winners[2] is None
    assert all(p >= 0 for p in prices)


def test_gsp_ordered_slots_and_pricing():
    """Generalized Second Price auction ordering and pricing."""
    a = AdSpot(3, ["music"], pos=[1.0, 0.6, 0.3])
    b1 = Bidder("A", {"music": 10.0})
    b2 = Bidder("B", {"music": 6.0})
    b3 = Bidder("C", {"music": 4.0})
    b4 = Bidder("D", {"music": 1.0})
    res = a.assign([b1, b2, b3, b4], method="gsp", valuation_fn=simple_valuation)
    winners, prices = res["winners"], res["prices"]

    assert winners == [b1, b2, b3]
    assert prices == [6.0, 4.0, 1.0]


def test_gsp_with_fewer_bidders_than_slots():
    """If fewer bidders than slots, remaining slots are unfilled."""
    a = AdSpot(3, ["x"], pos=[1.0, 0.5, 0.2])
    b1 = Bidder("A", {"x": 3.0})
    b2 = Bidder("B", {"x": 1.0})
    res = a.assign([b1, b2], method="gsp", valuation_fn=simple_valuation)
    winners = res["winners"]
    assert winners[0] == b1
    assert winners[1] == b2
    assert winners[2] is None


# ---------- Platform tests ----------

def test_platform_runs_multiple_auctions():
    """Verify Platform delegates to AdSpot.assign correctly."""
    a1 = AdSpot(1, ["a"])
    a2 = AdSpot(2, ["b"], pos=[1.0, 0.5])
    b1 = Bidder("B1", {"a": 2.0, "b": 1.0})
    b2 = Bidder("B2", {"b": 2.0})
    platform = Platform([b1, b2])

    res = platform.assign([a1, a2], method="first_price", valuation_fn=simple_valuation)
    assert isinstance(res, list)
    assert len(res) == 2
    for r in res:
        assert "winners" in r and "prices" in r


def test_platform_assign_raises_without_valuation_fn():
    """Missing valuation_fn in Platform.assign must raise."""
    p = Platform([Bidder("A", {"a": 1.0})])
    with pytest.raises(ValueError):
        p.assign([AdSpot(1, ["a"])])


# ---------- Tie-breaking behavior ----------

def test_random_tie_breaking_produces_valid_results():
    """Ensure tie-breaking uses randomness but still valid allocation."""
    a = AdSpot(2, ["a"])
    b1 = Bidder("A", {"a": 1.0})
    b2 = Bidder("B", {"a": 1.0})
    res = a.assign([b1, b2], method="first_price", valuation_fn=simple_valuation)
    assert set(res["winners"]).issubset({b1, b2})
    assert all(p >= 0 for p in res["prices"])


def test_platform_add_remove_clear_and_list_get():
    """Test add/remove/clear/list/get bidder functionality on Platform."""
    b1 = Bidder("B1", {"a": 1.0})
    b2 = Bidder("B2", {"a": 2.0})

    p = Platform([b1])
    # initial list
    assert p.list_bidders() == ["B1"]

    # add bidder
    p.add_bidder(b2)
    assert set(p.list_bidders()) == {"B1", "B2"}

    # get bidder by name
    assert p.get_bidder("B2") == b2
    assert p.get_bidder("nope") is None

    # remove bidder
    p.remove_bidder(b1)
    assert p.list_bidders() == ["B2"]

    # clear all bidders
    p.clear_bidders()
    assert p.list_bidders() == []


def test_remove_nonexistent_bidder_is_noop():
    """Removing a bidder that is not on the platform should not raise."""
    b1 = Bidder("B1", {"a": 1.0})
    b2 = Bidder("B2", {"a": 2.0})
    p = Platform([b1])
    # should not raise
    p.remove_bidder(b2)
    assert p.list_bidders() == ["B1"]


def test_platform_repr_and_str():
    """Check string representations of Platform."""
    b1 = Bidder("X", {"a": 1.0})
    b2 = Bidder("Y", {"a": 1.0})
    p = Platform([b1, b2])

    assert repr(p) == "Platform(2 bidders)"
    s = str(p)
    assert "Platform with 2 bidders" in s
    # ensure bidder names are included
    assert "X" in s and "Y" in s
