"""Bidder that participates in the auction"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from .ad_spot import AdSpot


class Bidder:
    """Represent a bidder participating in the ad auctions.

    Attributes:
        name (str): Unique identifier for the bidder.
        targeting (dict[str, float]): Expected value per click for each tag.
        bid_func (Optional[Callable]): Custom bidding strategy. Defaults to
            truthful bidding where the bid equals the bidder's valuation.
    """

    def __init__(
        self,
        name: str,
        targeting: dict[str, float],
        bid_func: Callable[[Self, AdSpot, float], float] | None = None,
    ):
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
        def truthful_bid(bidder: Bidder, adspot: AdSpot, valuation: float) -> float:
            return valuation

        self.bid_func = bid_func or truthful_bid

    def valuation(
        self,
        adspot: AdSpot,
        valuation_fn: Callable[[Self, AdSpot, list[float]], float],
        ctrs: list[float],
    ) -> float:
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
