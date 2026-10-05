# ad-auction-sim
Ad auction simulator for Game Theory and Control class at ETH Zurich

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first. The project requires Python 3.12 or newer.

> **NOTE:** This project is managed by `uv`. Always prefix repository commands with `uv run` so the project environment and dependencies are used correctly.

Run the demo:

```bash
uv run python demo.py
```

Run the tests:

```bash
uv run pytest -q
```

Run the notebooks in VS Code by selecting the `.venv` Python interpreter as the notebook kernel. 

The core simulator is in `sim/`, split in the files `bidder.py`, `ad_spot.py`, and `platform.py`.

For a short tutorial on the simulator, go check out the `demo` folder!

For the gender allocation experiment, play around with the notebook `experiments/auction_experiment.ipynb`!
