"""Configuaration file for the experiments"""

from collections.abc import Callable
from dataclasses import dataclass

from sim import AdSpot, Bidder

# Inputs: bidder, ad spot, CTRs for that bidder. Output: per-click valuation.
ValuationFn = Callable[[Bidder, AdSpot, list[float]], float]


@dataclass
class ExperimentConfig:
    """Configuration for an auction allocation experiment."""

    n_impressions: int
    seed: int

    # Auction mechanisms to evaluate.
    methods: list[str]

    # User groups from which impressions are sampled uniformly.
    genders: list[str]

    # Per-bidder valuation weights for each user group.
    bidder_targeting: dict[str, dict[str, float]]

    # Function used to compute each bidder's valuation for an ad spot.
    valuation_fn: ValuationFn
