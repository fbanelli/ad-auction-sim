from collections import Counter
import random
from typing import Dict, Any

from sim.ad_auction import Bidder, AdSpot, Platform


def simple_valuation(bidder: Bidder, adspot: AdSpot) -> float:
    return sum(bidder.targeting.get(tag, 0.0) for tag in adspot.tags)


def run_simulations(n_impressions: int = 2000, methods=None, seed: int = 0, valuation_fn: callable = simple_valuation) -> Dict[str, Any]:
    """Run simulations for a list of auction methods and collect stats.

    args:
        n_impressions: number of user impressions to simulate
        methods: list of auction methods to simulate (default: ["first_price", "second_price", "gsp"])
        seed: random seed for reproducibility
        valuation_fn: function to compute bidder's valuation for an ad spot

    Returns a dictionary mapping method -> stats, where stats contains per-gender counts,
    per-bidder spends, average prices, and share metrics.
    """
    if methods is None:
        methods = ["first_price", "second_price", "gsp"]

    random.seed(seed)

    # Define bidders with gender-specific targeting and valuations
    makeup = Bidder("Makeup", {"female": 5.0})
    stem = Bidder("STEM", {"female": 2.0, "male": 2.0})
    bidders = [makeup, stem]

    results = {}

    for method in methods:
        platform = Platform(bidders)
        counts = {"male": Counter(), "female": Counter()}
        total_spend = Counter()
        prices_list = []

        for _ in range(n_impressions):
            gender = random.choice(["male", "female"])  # 50/50 distribution
            spot = AdSpot(1, [gender])
            res = platform.assign([spot], method=method, valuation_fn=valuation_fn)[0]
            winner = res["winners"][0]
            price = res["prices"][0]
            prices_list.append(price)
            if winner is None:
                counts[gender]["none"] += 1
            else:
                counts[gender][winner.name] += 1
                total_spend[winner.name] += price

        # compute shares and summary
        summary = {
            "counts": counts,
            "total_spend": dict(total_spend),
            "avg_price": sum(prices_list) / len(prices_list) if prices_list else 0.0,
            "n_impressions": n_impressions,
        }
        # compute per-gender shares for each bidder
        shares = {"male": {}, "female": {}}
        for gender in ["female", "male"]:
            total = sum(counts[gender].values())
            for bidder_name, val in counts[gender].items():
                shares[gender][bidder_name] = val / total if total > 0 else 0.0

        summary["shares"] = shares
        results[method] = summary

    return results


def print_summary(results: Dict[str, Any]):
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
                for name in stats["counts"][g].keys():
                    if name not in bidders:
                        bidders.append(name)

            # prepare data
            data = {b: [stats["shares"][g].get(b, 0.0) for g in genders] for b in bidders}

            x = range(len(genders))
            width = 0.35

            fig, ax = plt.subplots()
            for i, (b, vals) in enumerate(data.items()):
                ax.bar([p + i * width for p in x], vals, width, label=b)

            ax.set_xticks([p + width * (len(data) - 1) / 2 for p in x])
            ax.set_xticklabels(genders)
            ax.set_ylabel('Share of wins')
            ax.set_title(f'Share by bidder and gender ({method})')
            ax.legend()

            fig_path = f"{out_prefix}/share_by_gender_{method}.png"
            fig.savefig(fig_path)
            plt.close(fig)
            print(f"Saved plot to {fig_path}")

    except Exception as e:
        print("Plotting skipped (matplotlib not available or error):", e)


if __name__ == "__main__":
    results = run_simulations(n_impressions=2000, methods=["first_price", "second_price", "gsp"], seed=1)
    print_summary(results)
    try_plot(results)

