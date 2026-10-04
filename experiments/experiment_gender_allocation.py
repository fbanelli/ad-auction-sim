import random
from collections import Counter
from typing import Any

from experiments.config import ExperimentConfig
from sim import AdSpot, Bidder, Platform


def simple_valuation(bidder: Bidder, adspot: AdSpot, ctrs=None) -> float:
    # Backwards-compatible: accept optional ctrs (ignored) so this function can be
    # directly passed to the simulator which provides ctrs per bidder.
    return sum(bidder.targeting.get(tag, 0.0) for tag in adspot.tags)


def run_simulations(config: ExperimentConfig) -> dict[str, Any]:
    """Run the configured auction experiment and collect summary statistics.

    Args:
        config: Experiment configuration containing the auction methods,
            bidders, population groups, valuation function, random seed,
            and number of impressions.

    Returns:
        Dictionary mapping each auction method to its summary statistics.
    """
    random.seed(config.seed)

    bidders = [
        Bidder(name, targeting) for name, targeting in config.bidder_targeting.items()
    ]

    results = {}

    for method in config.methods:
        platform = Platform(bidders)

        counts = {gender: Counter() for gender in config.genders}
        total_spend = Counter()
        prices = []

        for _ in range(config.n_impressions):
            gender = random.choice(config.genders)
            spot = AdSpot(1, [gender])

            result = platform.assign(
                [spot],
                method=method,
                valuation_fn=config.valuation_fn,
            )[0]

            winner = result["winners"][0]
            price = result["prices"][0]

            prices.append(price)

            if winner is None:
                counts[gender]["none"] += 1
            else:
                counts[gender][winner.name] += 1
                total_spend[winner.name] += price

        shares = {gender: {} for gender in config.genders}

        for gender in config.genders:
            total = sum(counts[gender].values())

            for bidder_name, count in counts[gender].items():
                shares[gender][bidder_name] = count / total if total > 0 else 0.0

        results[method] = {
            "counts": counts,
            "shares": shares,
            "total_spend": dict(total_spend),
            "avg_price": sum(prices) / len(prices) if prices else 0.0,
            "n_impressions": config.n_impressions,
            "genders": config.genders,
        }

    return results


def print_summary(results: dict[str, Any]):
    for method, stats in results.items():
        print("\nMethod:", method)
        print(f"Total impressions: {stats['n_impressions']}")
        print(f"Average price per impression: {stats['avg_price']:.3f}")
        print("Total spend by bidder:")
        for b, s in stats["total_spend"].items():
            print(f"  {b}: {s:.2f}")
        for gender in ["female", "male"]:
            total = sum(stats["counts"][gender].values())
            print(f"Impressions for {gender}: {total}")
            for name, cnt in stats["counts"][gender].most_common():
                share = stats["shares"][gender].get(name, 0.0)
                print(f"  {name}: {cnt} ({share:.2%})")


def try_plot(results, out_prefix: str = "experiments/output"):
    try:
        import os

        import matplotlib.pyplot as plt

        os.makedirs(out_prefix, exist_ok=True)

        for method, stats in results.items():
            # bar chart: share by bidder for each gender
            genders = ["female", "male"]
            bidders = []
            for g in genders:
                for name in stats["counts"][g]:
                    if name not in bidders:
                        bidders.append(name)

            # prepare data
            data = {
                b: [stats["shares"][g].get(b, 0.0) for g in genders] for b in bidders
            }

            x = range(len(genders))
            width = 0.35

            fig, ax = plt.subplots()
            for i, (b, vals) in enumerate(data.items()):
                ax.bar([p + i * width for p in x], vals, width, label=b)

            ax.set_xticks([p + width * (len(data) - 1) / 2 for p in x])
            ax.set_xticklabels(genders)
            ax.set_ylabel("Share of wins")
            ax.set_title(f"Share by bidder and gender ({method})")
            ax.legend()

            fig_path = f"{out_prefix}/share_by_gender_{method}.png"
            fig.savefig(fig_path)
            plt.close(fig)
            print(f"Saved plot to {fig_path}")

    except Exception as e:  # noqa: BLE001
        print("Plotting skipped (matplotlib not available or error):", e)
