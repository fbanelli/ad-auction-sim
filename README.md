# ad-auction-sim
Ad auction simulator for Game Theory and Control class at ETH Zurich

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first. The project requires Python 3.12 or newer; `uv` will create and synchronize the project environment automatically.

Run the demo:

```bash
uv run python demo.py
```

Run the tests:

```bash
uv run pytest -q
```

Run the notebooks in VS Code by selecting the `.venv` Python interpreter as the notebook kernel. 

For commands in this repository, prefix them with `uv run`.

The core simulator is in `sim/ad_auction.py` with classes `Bidder`, `AdSpot`, and `Platform`.

For a short tutorial on the simulator, go check out the `demo` folder! 

This repository is a small classroom project. You do not need to install it as a package to run the demo or tests.