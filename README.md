# IQM Research Award 2026: Leggett-Garg Inequality-based Quantum Computers Quality Benchmark

About ...

## Technical summary

- **FakeBackend**. In order to simulate `FakeSirius`, we prepared the `simulator` module of the project. Within it, we implemented not only the `FakeSirius` method, which creates the `sirius` computer simulator from the calibration and performance quality data. However, the module also contains functionalities that allows for creation of general IQM backend simulator from a real device, via `FakeFromBackend` method. The module is fully documented.

## Setup

Prepare the environemnt with:

```
uv sync
```

Remember to set environmental variables. In particular:

- IQM_TOKEN
- IQM_PROVIDER
- IQM_COMPUTER

Also, ensure that `PYTHONPATH` contains the main folder of the project (or `'.'`).

## Running the scripts

Once the setup is complete use

```
uv run <script/path>
```

from the main folder, to call the desired script.
