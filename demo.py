from typing import List
from sim.ad_auction import Bidder, AdSpot, Platform


def simple_valuation(bidder: Bidder, adspot: AdSpot, ctrs: List[float]) -> float:
    """Compute the bidder's valuation for a given ad spot.

    The valuation is the sum of the bidder’s targeting weights corresponding
    to the ad spot’s tags. Missing tags in the bidder's targeting map are
    treated as zero contribution.

    Args:
        bidder (Bidder): The bidder evaluating the ad spot.
        adspot (AdSpot): The ad spot being evaluated.

    Returns:
        float: The total valuation score.

    Examples:
        >>> b = Bidder("A", {"sports": 3.0, "tech": 2.0})
        >>> s = AdSpot(1, ["sports", "male"], ctrs=[1.0])
        >>> simple_valuation(b, s)
        3.0
    """
    val = 0.0
    for t in adspot.tags:
        # Tags not in bidder's targeting dictionary contribute zero.
        val += bidder.targeting.get(t, 0.0)
    return val


def main():
    """Run a demo auction across multiple pricing methods.

    Initializes sample bidders and ad spots, then runs `Platform.assign`
    under three auction rules: first-price, second-price, and generalized
    second-price (GSP). Prints winners and clearing prices for each spot.

    Examples:
        $ python demo.py
        Method: first_price
        AdSpot 0: winners=['Alpha'], prices=[...]
    """
    bidders = [
        Bidder("Alpha", {"sports": 4.0, "male": 1.0}),
        Bidder("Beta", {"sports": 3.0}),
        Bidder("Gamma", {"female": 2.0}),
    ]

    spots = [
        AdSpot(2, ["sports", "male"], pos=[0.9, 0.5]),
        AdSpot(1, ["female"], pos=[1.0]),
    ]

    platform = Platform(bidders)

    for method in ["first_price", "second_price", "gsp"]:
        print("\nMethod:", method)
        # The valuation_fn defines how bidders value each spot.
        results = platform.assign(spots, method=method, valuation_fn=simple_valuation)
        for i, r in enumerate(results):
            print(f"AdSpot {i}: winners={r['winners']}, prices={r['prices']}")


if __name__ == "__main__":
    main()
