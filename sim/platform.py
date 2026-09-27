"""Platform that assigns ad spots to bidders"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ad_spot import AdSpot
    from .bidder import Bidder


class Platform:
    """Manage a set of bidders and coordinate auctions across multiple adspots."""

    def __init__(self, bidders: list[Bidder]):
        """Initialize the platform with a bidder list.

        Args:
            bidders (list[Bidder]): Registered participants on the platform.
        """
        self.bidders = list(bidders)

    def assign(
        self,
        adspots: list[AdSpot],
        method: str = "second_price",
        valuation_fn: Callable[[Bidder, AdSpot, list[float]], float] | None = None,
    ) -> list[dict[str, list]]:
        """Run auctions for multiple adspots sequentially.

        Args:
            adspots (list[AdSpot]): list of ad opportunities to allocate.
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
            # Quality of ad (in reality is given by machine learning model, here we simulate it with random values)
            Qs = [random.uniform(0.1, 0.9) for _ in self.bidders]

            # Delegates the auction logic to each AdSpot instance.
            res = spot.assign(
                self.bidders, method=method, valuation_fn=valuation_fn, Qs=Qs
            )

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
            print(f"WARNING: Bidder {bidder.name} not found on platform.")
            # previously this would raise; make remove operation tolerant
            return

    def clear_bidders(self):
        """Remove all bidders from the platform."""
        self.bidders = []

    def __repr__(self) -> str:
        return f"Platform({len(self.bidders)} bidders)"

    def __str__(self) -> str:
        return f"Platform with {len(self.bidders)} bidders: {[b.name for b in self.bidders]}"

    def list_bidders(self) -> list[str]:
        """Return a list of bidder names currently on the platform."""
        return [b.name for b in self.bidders]

    def get_bidder(self, name: str) -> Bidder | None:
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
