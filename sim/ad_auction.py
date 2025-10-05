from __future__ import annotations

import random
from typing import Dict, List, Callable, Optional, Tuple


class Bidder:
    """Represent a bidder participating in ad auctions.

    Attributes:
        name (str): Unique identifier for the bidder.
        targeting (dict[str, float]): Expected quality score per audience tag.
        bid_func (Optional[Callable]): Custom bidding strategy. Defaults to
            truthful bidding where the bid equals the bidder's valuation.
    """

    def __init__(self, name: str, targeting: Dict[str, float],
                 bid_func: Optional[Callable] = None):
        """Initialize a Bidder.

        Args:
            name (str): Bidder identifier.
            targeting (dict[str, float]): Mapping from tag to expected quality.
            bid_func (Optional[Callable]): Function (bidder, adspot, valuation)
                -> bid amount. Defaults to truthful bidding.

        Examples:
            >>> bidder = Bidder("A", {"sports": 0.8})
            >>> bidder.bid(None, 0.5)
            0.5
        """
        self.name = name
        self.targeting = targeting
        self.bid_func = bid_func or (lambda bidder, adspot, valuation: valuation)

    def valuation(self, adspot, valuation_fn: Callable[['Bidder', 'AdSpot'], float]) -> float:
        """Compute the bidder's valuation for a given adspot.

        Args:
            adspot (AdSpot): The ad opportunity being evaluated.
            valuation_fn (Callable): Function (bidder, adspot) -> value.

        Returns:
            float: The computed valuation for this adspot.
        """
        return valuation_fn(self, adspot)

    def bid(self, adspot, valuation: float) -> float:
        """Compute the bidder's submitted bid.

        Args:
            adspot (AdSpot): Ad placement opportunity.
            valuation (float): Bidder's valuation for this adspot.

        Returns:
            float: Bid amount produced by `bid_func`.
        """
        return float(self.bid_func(self, adspot, valuation))

    def __repr__(self) -> str:
        return f"Bidder({self.name})"


class AdSpot:
    """Represent an ad placement opportunity (auctioned slot set).

    Attributes:
        num_spots (int): Number of ad slots available.
        tags (list[str]): Contextual tags describing the user/environment.
        ctrs (list[float]): Expected click-through rates per slot.
    """

    def __init__(self, num_spots: int, tags: List[str], ctrs: Optional[List[float]] = None):
        """Initialize an AdSpot.

        Args:
            num_spots (int): Number of available ad slots (>=1).
            tags (list[str]): Descriptive tags for the impression context.
            ctrs (Optional[list[float]]): CTRs for each slot. Defaults to uniform 1.0.

        Raises:
            AssertionError: If `num_spots` < 1.
            ValueError: If length of `ctrs` != `num_spots`.
        """
        assert num_spots >= 1
        self.num_spots = num_spots
        self.tags = list(tags)
        if ctrs is None:
            # Default uniform CTRs ensure equal slot quality when not specified.
            self.ctrs = [1.0 for _ in range(num_spots)]
        else:
            if len(ctrs) != num_spots:
                raise ValueError("ctrs length must equal num_spots")
            self.ctrs = list(ctrs)

    def assign(
        self,
        bidders: List[Bidder],
        method: str = "second_price",
        valuation_fn: Optional[Callable[[Bidder, 'AdSpot'], float]] = None,
    ) -> Dict[str, List]:
        """Run an auction among bidders for this adspot.

        Args:
            bidders (list[Bidder]): Participants in the auction.
            method (str): Auction type, one of {'first_price', 'second_price', 'gsp'}.
            valuation_fn (Callable): Function (bidder, adspot) -> valuation.

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

        method = method.lower()
        if method not in {"first_price", "second_price", "gsp"}:
            raise ValueError(f"unknown method: {method}")

        # Compute eligible bidders with positive valuations.
        eligible = []
        for b in bidders:
            val = b.valuation(self, valuation_fn)
            if val > 0:
                bid_amt = b.bid(self, val)
                eligible.append((b, val, bid_amt))

        # If no one bids positively, return empty allocation.
        if not eligible:
            return {"winners": [None] * self.num_spots, "prices": [0.0] * self.num_spots}

        # Sort descending by bid, breaking ties randomly for fairness.
        def sort_key(item: Tuple[Bidder, float, float]):
            return (item[2], random.random())

        eligible_sorted = sorted(eligible, key=sort_key, reverse=True)
        winners: List[Optional[Bidder]] = [None] * self.num_spots
        prices: List[float] = [0.0] * self.num_spots

        if method in {"first_price", "second_price"}:
            # Allocate top bidders to identical spots.
            allocated = eligible_sorted[: self.num_spots]
            for i, (bidder, val, bid_amt) in enumerate(allocated):
                winners[i] = bidder
                if method == "first_price":
                    prices[i] = bid_amt
                else:
                    prices[i] = eligible_sorted[i + 1][2] if i + 1 < len(eligible_sorted) else 0.0

        elif method == "gsp":
            # Generalized Second Price: ordered slots with descending CTRs.
            allocated = eligible_sorted[: self.num_spots]
            for slot_idx, (bidder, val, bid_amt) in enumerate(allocated):
                winners[slot_idx] = bidder
                # Price is the next *overall* bidder's bid (not just among winners)
                if slot_idx + 1 < len(eligible_sorted):
                    prices[slot_idx] = eligible_sorted[slot_idx + 1][2]
                else:
                    prices[slot_idx] = 0.0


        return {"winners": winners, "prices": prices}


class Platform:
    """Manage a set of bidders and coordinate auctions across multiple adspots."""

    def __init__(self, bidders: List[Bidder]):
        """Initialize the platform with a bidder list.

        Args:
            bidders (list[Bidder]): Registered participants on the platform.
        """
        self.bidders = list(bidders)

    def assign(
        self,
        adspots: List[AdSpot],
        method: str = "second_price",
        valuation_fn: Optional[Callable[[Bidder, AdSpot], float]] = None,
    ) -> List[Dict[str, List]]:
        """Run auctions for multiple adspots sequentially.

        Args:
            adspots (list[AdSpot]): List of ad opportunities to allocate.
            method (str): Auction format, defaults to 'second_price'.
            valuation_fn (Callable): Function (bidder, adspot) -> valuation.

        Returns:
            list[dict[str, list]]: Results per adspot, each with 'winners' and 'prices'.

        Raises:
            ValueError: If `valuation_fn` is not provided.
        """
        if valuation_fn is None:
            raise ValueError("valuation_fn must be provided")

        results = []
        for spot in adspots:
            # Delegates the auction logic to each AdSpot instance.
            res = spot.assign(self.bidders, method=method, valuation_fn=valuation_fn)
            results.append(res)
        return results
