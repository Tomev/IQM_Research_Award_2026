"""A script demonstrating the usage of the `IQMStarCostEvaluator` for qubit layout selection.

This script generates a test quantum circuit using the LGACZ2 job configuration and demonstrates how to use the
`IQMStarCostEvaluator` to find the best qubit layouts for a given quantum circuit on an IQM backend. It also shows a
placeholder for the original IQM Qubit Selector, which is currently not supported for star topology devices.

.. note::
    IQM Qubit Selector is programmed to work with the crystal topology devices. It is currently not supported for star
    topology devices, hence the `iqm_qubit_selection` function is commented out and marked as a TODO.
"""

import os

from iqm.qiskit_iqm import IQMBackend, IQMProvider
from iqm.qubit_selector.qubit_selector import CostEvaluator
from qiskit.circuit.quantumcircuit import QuantumCircuit

from src.jobs import LGACZ2
from src.selector import IQMStarCostEvaluator


def get_lg_circuit() -> QuantumCircuit:
    """Generates a test circuit using the LGACZ2 job configuration"""
    qubits_list: list[list[int]] = [[1, 0, 2]]
    job: LGACZ2 = LGACZ2()
    job.n_repetitions = 1
    job.add_test_circuits(qubits_list, 0.1)
    return job.circuits[0]  # Do not transpile it, because it causes problems with "move" gate later!


def main() -> None:
    # iqm_qubit_selection()
    custom_qubit_seleciton()


def custom_qubit_seleciton() -> None:
    """Proof of concept for `IQMStarCostEvaluator` class usage.

    Demonstrates how to use the `IQMStarCostEvaluator` to find the best qubit layouts for a given quantum circuit on an
    IQM backend.
    """
    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
    )
    backend: IQMBackend = provider.get_backend()

    n_best_layouts: int = 10
    circuit: QuantumCircuit = get_lg_circuit()

    cost_evaluator: IQMStarCostEvaluator = IQMStarCostEvaluator(backend, circuit)

    best_layouts: list[tuple[tuple[int, ...], float]] = cost_evaluator.get_top_layouts(n_best_layouts)

    print(f"Best {n_best_layouts} layouts with errors:")
    for layout in best_layouts:
        print(f"\t{layout}")


def iqm_qubit_selection() -> None:
    """TODO(TR): Docstring

    .. note::
        Dropped for now, due to the lack of IQM Qubit Selector support for star topology devices.
    """

    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
        # quantum_computer="garnet",
    )
    backend: IQMBackend = provider.get_backend()

    n_best_layouts: int = 3
    circuit: QuantumCircuit = get_lg_circuit()

    layouts, cost = CostEvaluator(backend=backend, quantum_circuit=circuit).get_top_layouts(num_layouts=n_best_layouts)
    print(f"Top {n_best_layouts} qiskit layouts and their costs:")
    for layout, c in zip(layouts[:n_best_layouts], cost[:n_best_layouts]):
        print(f"Layout: {layout}, Cost: {c * 100:.2f}%")


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
