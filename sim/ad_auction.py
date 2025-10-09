from __future__ import annotations

import random
from typing import Dict, List, Callable, Optional, Tuple


class Bidder:
    """Represent a bidder participating in the ad auctions.

    Attributes:
        name (str): Unique identifier for the bidder.
        targeting (dict[str, float]): Expected value per click for each tag.
        bid_func (Optional[Callable]): Custom bidding strategy. Defaults to
            truthful bidding where the bid equals the bidder's valuation.
    """

    def __init__(self, name: str, targeting: Dict[str, float], 
                bid_func: Optional[Callable[['Bidder', 'AdSpot', float], float]] = None):
        """Initialize a Bidder.

        Args:
            name (str): Bidder identifier.
            targeting (dict[str, float]): Mapping from tag to expected value per click.
            bid_func (Optional[Callable]): Function (bidder, adspot, valuation)
                -> bid amount. Defaults to truthful bidding.

        Examples:
            >>> bidder = Bidder("A", {"sports": 0.8})
            >>> bidder.bid(None, 0.5)
            0.5
        """
        self.name = name
        self.targeting = targeting 

        # default to truthful bidding
        def truthful_bid(bidder: 'Bidder', adspot: 'AdSpot', valuation: float) -> float:
            return valuation
        self.bid_func = bid_func or truthful_bid

    def valuation(self, adspot: AdSpot, valuation_fn: Callable[['Bidder', 'AdSpot', List[float]], float], ctrs: List[float]) -> float:
        """Compute the bidder's valuation for a given adspot.

        Args:
            adspot (AdSpot): The ad opportunity being evaluated.
            valuation_fn (Callable): Function (bidder, adspot, ctrs) -> valuation.
            ctrs (list[float]): Expected click-through rates per slot for this bidder.

        Returns:
            float: The computed valuation for this adspot.
        """
        return valuation_fn(self, adspot, ctrs)

    def bid(self, adspot: AdSpot, valuation: float) -> float:
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
        num_slots (int): Number of ad slots available.
        tags (list[str]): Contextual tags describing the user/environment.
        pos (list[float]): Expected position scores per slot. 
    """

    def __init__(self, num_slots: int, tags: List[str], pos: Optional[List[float]] = None):
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
        bidders: List[Bidder],
        method: str = "second_price",
        valuation_fn: Optional[Callable[[Bidder, 'AdSpot', List[float]], float]] = None,
        Qs: Optional[List[float]] = None
    ) -> Dict[str, List]:
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
            ctrs = [Qs[i] * p for p in self.pos]  # Effective CTRs per slot for this bidder
            val = b.valuation(self, valuation_fn, ctrs)
            if val > 0:
                bid_amt = b.bid(self, val)
                eligible.append((b, val, bid_amt, Qs[i]))  # (bidder, how much they value the spot, how much they bid, quality score)

        # If no one bids positively, return empty allocation.
        if not eligible:
            return {"winners": [None] * self.num_slots, "prices": [0.0] * self.num_slots}


        # Here you can change how winners are determined, here is the classic rank-by-expected-value (bid * quality)
        ###############################################

        # Sort descending by bid, breaking ties randomly for fairness.
        def sort_key(item: Tuple[Bidder, float, float, float]):
            bidder, val, bid_amt, quality = item
            return (bid_amt * quality, random.random())
        eligible_sorted = sorted(eligible, key=sort_key, reverse=True)

        ###############################################


        winners: List[Optional[Bidder]] = [None] * self.num_slots
        prices: List[float] = [0.0] * self.num_slots

        if method in {"first_price", "second_price"}:
            # Allocate top bidders to identical slots.
            allocated = eligible_sorted[: self.num_slots]
            for i, (bidder, val, bid_amt, quality) in enumerate(allocated):
                winners[i] = bidder
                if method == "first_price":
                    prices[i] = bid_amt
                else:
                    prices[i] = eligible_sorted[i + 1][2] if i + 1 < len(eligible_sorted) else 0.0

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
        valuation_fn: Optional[Callable[[Bidder, AdSpot, List[float]], float]] = None,
    ) -> List[Dict[str, List]]:
        """Run auctions for multiple adspots sequentially.

        Args:
            adspots (list[AdSpot]): List of ad opportunities to allocate.
            method (str): Auction format, defaults to 'second_price'.
            valuation_fn (Callable): Function (bidder, adspot, ctrs) -> valuation.

        Returns:
            list[dict[str, list]]: Results per adspot, each with 'winners' and 'prices'.

        Raises:
            ValueError: If `valuation_fn` is not provided.
        """
        if valuation_fn is None:
            raise ValueError("valuation_fn must be provided")

        results = []
        for spot in adspots:
            # quality of ad (in reality is given by machine learning model, here we simulate it with random values)
            Qs = [random.uniform(0.1, 0.9) for _ in self.bidders]

            # Delegates the auction logic to each AdSpot instance.
            res = spot.assign(self.bidders, method=method, valuation_fn=valuation_fn, Qs=Qs)

            results.append(res)
        return results

    def add_bidder(self, bidder: Bidder):
        """Add a new bidder to the platform.

        Args:
            bidder (Bidder): The bidder to add.
        """
        self.bidders.append(bidder)
        
    def remove_bidder(self, bidder: Bidder):
        """Remove a bidder from the platform.

        Args:
            bidder (Bidder): The bidder to remove.
        """
        # If bidder is not present, do nothing (idempotent remove).
        try:
            self.bidders.remove(bidder)
        except ValueError:
            # previously this would raise; make remove operation tolerant
            return
        
    def clear_bidders(self):
        """Remove all bidders from the platform."""
        self.bidders = []
        
    def __repr__(self) -> str:
        return f"Platform({len(self.bidders)} bidders)"
    
    def __str__(self) -> str:
        return f"Platform with {len(self.bidders)} bidders: {[b.name for b in self.bidders]}"
    
    def list_bidders(self) -> List[str]:
        """Return a list of bidder names currently on the platform."""
        return [b.name for b in self.bidders]
    
    def get_bidder(self, name: str) -> Optional[Bidder]:
        """Retrieve a bidder by name.

        Args:
            name (str): The name of the bidder to retrieve.

        Returns:
            Optional[Bidder]: The bidder with the given name, or None if not found.
        """
        for b in self.bidders:
            if b.name == name:
                return b
        return None