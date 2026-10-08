"""Class that represents an ad placement spot"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bidder import Bidder


class AdSpot:
    """Represent an ad placement opportunity (auctioned slot set).

    Attributes:
        num_slots (int): Number of ad slots available.
        tags (list[str]): Contextual tags describing the user/environment.
        pos (list[float]): Expected position scores per slot.
    """

    def __init__(
        self, num_slots: int, tags: list[str], pos: list[float] | None = None
    ) -> None:
        """Initialize an AdSpot.

        Args:
            num_slots: Number of available ad slots (>=1).
            tags: Descriptive tags for the impression context.
            pos: Expected position scores per slot. (i.e. Probability of click in that position)

        Raises:
            AssertionError: If `num_slots` < 1.
            ValueError: If length of `pos` != `num_slots`.
            ValueError: If any value in `pos` is not in [0, 1].
        """
        assert num_slots >= 1, "num_slots must be at least 1"
        self.num_slots = num_slots
        self.tags = list(tags)
        if pos is None:
            # Default uniform positions ensure equal slot quality when not specified.
            self.pos = [1.0 for _ in range(num_slots)]
        else:
            if len(pos) != num_slots:
                raise ValueError("pos length must equal num_slots")
            elif any(p < 0 or p > 1 for p in pos):
                raise ValueError("pos values must be between 0 and 1")
            self.pos = list(pos)

    def assign(
        self,
        bidders: list[Bidder],
        method: str = "gsp",
        valuation_fn: Callable[[Bidder, AdSpot, list[float]], float] | None = None,
        Qs: list[float] | None = None,
    ) -> dict[str, list]:
        """Run an auction among bidders for this adspot.

        Args:
            bidders: Participants in the auction.
            method: Auction type, one of {'first_price', 'gsp'}.
            valuation_fn: Function (bidder, adspot, ctrs) -> per-click valuation.

        Returns:
            Dictionary with keys:
                - 'winners': list of winning bidders (or None if no bids)
                - 'prices': list of per-click clearing prices per slot
                - 'effective_ctrs': effective winner CTR per slot (zero if unfilled)

        Raises:
            ValueError: If `valuation_fn` is not provided or `method` unknown.
            ValueError: If GSP is requested with a non-positive quality.

        Notes:
            - GSP requires strictly positive qualities and charges the minimum
              bids needed to retain each rank.
        """
        if valuation_fn is None:
            raise ValueError("valuation_fn must be provided")

        if Qs is None:
            Qs = [1.0 for _ in bidders]  # Default quality scores if none provided
        elif len(Qs) != len(bidders):
            raise ValueError("Length of Qs must match number of bidders")

        method = method.lower()
        if method not in {"first_price", "gsp"}:
            raise ValueError(f"unknown method: {method}")
        if method == "gsp" and any(not (quality > 0) for quality in Qs):
            raise ValueError("GSP requires all qualities to be strictly positive")

        # Compute eligible bidders with positive valuations.
        eligible = []
        for i, b in enumerate(bidders):
            ctrs = [
                Qs[i] * p for p in self.pos
            ]  # Effective CTRs per slot for this bidder
            val = b.valuation(self, valuation_fn, ctrs)
            if val > 0:
                bid_amt = b.bid(self, val)
                eligible.append(
                    (b, val, bid_amt, Qs[i])
                )  # (bidder, how much they value the spot, how much they bid, quality score)

        # If no one bids positively, return empty allocation.
        if not eligible:
            return {
                "winners": [None] * self.num_slots,
                "prices": [0.0] * self.num_slots,
                "effective_ctrs": [0.0] * self.num_slots,
            }

        # Here you can change how winners are determined, here is the classic rank-by-expected-value (bid * quality)
        ###############################################

        # Sort descending by bid, breaking ties randomly for fairness.
        def sort_key(
            item: tuple[Bidder, float, float, float],
        ) -> tuple[float, float]:
            _, _, bid_amt, quality = item
            return (bid_amt * quality, random.random())

        eligible_sorted = sorted(eligible, key=sort_key, reverse=True)

        ###############################################

        winners: list[Bidder | None] = [None] * self.num_slots
        prices: list[float] = [0.0] * self.num_slots
        effective_ctrs: list[float] = [0.0] * self.num_slots

        if method == "first_price":
            # Allocate top bidders to identical slots.
            allocated = eligible_sorted[: self.num_slots]
            for i, (bidder, val, bid_amt, quality) in enumerate(allocated):
                winners[i] = bidder
                prices[i] = bid_amt
                effective_ctrs[i] = quality * self.pos[i]

        elif method == "gsp":
            # Generalized Second Price: ordered slots with descending CTRs.
            allocated = eligible_sorted[: self.num_slots]
            for slot_idx, (bidder, val, bid_amt, quality) in enumerate(allocated):
                winners[slot_idx] = bidder
                effective_ctrs[slot_idx] = quality * self.pos[slot_idx]
                # Price is based on the next *overall* bidder (not just winners).
                if slot_idx + 1 < len(eligible_sorted):
                    _, _, next_bid, next_quality = eligible_sorted[slot_idx + 1]
                    prices[slot_idx] = (next_quality * next_bid) / quality
                else:
                    prices[slot_idx] = 0.0

        # Here you can add a method, e.g., VCG, if desired.
        ###############################################

        ###############################################

        return {
            "winners": winners,
            "prices": prices,
            "effective_ctrs": effective_ctrs,
        }
