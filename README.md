# IQM Research Award 2026: Leggett-Garg Inequality-based Quantum Computers Quality Benchmark

About ...

## Technical summary

- **FakeBackend**. In order to simulate `FakeSirius`, we prepared the `simulator` module of the project. Within it, we implemented not only the `FakeSirius` method, which creates the `sirius` computer simulator from the calibration and performance quality data. However, the module also contains functionalities that allows for creation of general IQM backend simulator from a real device, via `FakeFromBackend` method. The module is fully documented.
- **QubitSelector**. We initially planned to use `IQM Qubit Selector` to select the best qubit sets for our experiments. However, we noticed that it's only compatible with the crystal topology type devices. We tried to hotfix this issue, but resigned in the process. The reason behind our resignation is the assessment that the IQM technological stack is ill prepared to properly handle star topology devices using current tools. There is a difference between how the central resonator is treated in the `IQMBackend` objects (as separate entity) and `IQMCircuits` (essentially as qubits). Handling this problem properly, would require preparing the whole techonological stack in such a fashion that it would be able to differentiate between qubits and central resonators, and actually treat them commonly where needed, and separately otherwise. Such decisions should be made at the level of the CTO of the company, not by a reseach competition participants. Instead, we implemented and used `IQMStarCostEvaluator`, which returns best qubits layouts for a given circuit and a given star topology backend. The `IQMStarCostEvaluator` class implementation can be found in the `selector.py` module and is fully documented.

## Setup

Prepare the environemnt with:

```
uv sync
```

Remember to set environmental variables. In particular:

- `IQM_TOKEN`
- `IQM_PROVIDER`
- `IQM_COMPUTER`

Also, ensure that `PYTHONPATH` contains the main folder of the project (or `'.'`).

To run the analysis scripts setting `EXP_DATA_PATH` environmental variable is required.

## Running the scripts

Once the setup is complete use

```
uv run <script/path>
```

from the main folder, to call the desired script.
