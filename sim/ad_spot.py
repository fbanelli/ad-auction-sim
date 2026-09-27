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

    def __init__(self, num_slots: int, tags: list[str], pos: list[float] | None = None):
        """Initialize an AdSpot.

        Args:
            num_slots (int): Number of available ad slots (>=1).
            tags (list[str]): Descriptive tags for the impression context.
            pos (list[float]): Expected position scores per slot. (i.e. Probability of click in that position)

        Raises:
            AssertionError: If `num_slots` < 1.
            ValueError: If length of `pos` != `num_slots`.
            ValueError: If any value in `pos` is not in [0, 1].
        """
        assert num_slots >= 1
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
        method: str = "second_price",
        valuation_fn: Callable[[Bidder, AdSpot, list[float]], float] | None = None,
        Qs: list[float] | None = None,
    ) -> dict[str, list]:
        """Run an auction among bidders for this adspot.

        Args:
            bidders (list[Bidder]): Participants in the auction.
            method (str): Auction type, one of {'first_price', 'second_price', 'gsp'}.
            valuation_fn (Callable): Function (bidder, adspot, ctrs) -> valuation.

        Returns:
            dict[str, list]: A dictionary with keys:
                - 'winners': list of winning bidders (or None if no bids)
                - 'prices': list of clearing prices per slot

        Raises:
            ValueError: If `valuation_fn` is not provided or `method` unknown.

        Notes:
            - In second-price auctions, winners pay the next-highest bid.
            - In GSP, prices correspond to the next bidder’s bid per slot.
        """
        if valuation_fn is None:
            raise ValueError("valuation_fn must be provided")

        if Qs is None:
            Qs = [1.0 for _ in bidders]  # Default quality scores if none provided
        elif len(Qs) != len(bidders):
            raise ValueError("Length of Qs must match number of bidders")

        method = method.lower()
        if method not in {"first_price", "second_price", "gsp"}:
            raise ValueError(f"unknown method: {method}")

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
            }

        # Here you can change how winners are determined, here is the classic rank-by-expected-value (bid * quality)
        ###############################################

        # Sort descending by bid, breaking ties randomly for fairness.
        def sort_key(item: tuple[Bidder, float, float, float]):
            _, _, bid_amt, quality = item
            return (bid_amt * quality, random.random())

        eligible_sorted = sorted(eligible, key=sort_key, reverse=True)

        ###############################################

        winners: list[Bidder | None] = [None] * self.num_slots
        prices: list[float] = [0.0] * self.num_slots

        if method in {"first_price", "second_price"}:
            # Allocate top bidders to identical slots.
            allocated = eligible_sorted[: self.num_slots]
            for i, (bidder, val, bid_amt, quality) in enumerate(allocated):
                winners[i] = bidder
                if method == "first_price":
                    prices[i] = bid_amt
                else:
                    prices[i] = (
                        eligible_sorted[i + 1][2]
                        if i + 1 < len(eligible_sorted)
                        else 0.0
                    )

        elif method == "gsp":
            # Generalized Second Price: ordered slots with descending CTRs.
            allocated = eligible_sorted[: self.num_slots]
            for slot_idx, (bidder, val, bid_amt, quality) in enumerate(allocated):
                winners[slot_idx] = bidder
                # Price is the next *overall* bidder's bid (not just among winners)
                if slot_idx + 1 < len(eligible_sorted):
                    prices[slot_idx] = eligible_sorted[slot_idx + 1][2]
                else:
                    prices[slot_idx] = 0.0

        # Here you can add a method, e.g., VCG, if desired.
        ###############################################

        ###############################################

        return {"winners": winners, "prices": prices}
