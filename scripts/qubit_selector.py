"""A module with qubit selector training

.. note::
    IQM Qubit Selector is programmed to work with the crystal topology devices. It
"""

import os
from itertools import combinations, permutations

from iqm.iqm_client import IQMClient
from iqm.qiskit_iqm import IQMBackend, IQMProvider, transpile_to_IQM
from iqm.qubit_selector.qubit_selector import CostEvaluator
from iqm.station_control.interface.models import ObservationSetWithObservations
from qiskit import transpile
from qiskit.circuit.quantumcircuit import QuantumCircuit
from tqdm import tqdm

from src.jobs import LGACZ2


def get_operation_errors(system_name: str) -> dict[str, float]:
    """TODO(TR): Docstring

    errors are (1 - fidelity)
    """
    client: IQMClient = IQMClient(
        iqm_server_url=os.environ["IQM_PROVIDER"],
        quantum_computer=system_name,
    )

    calibration_set: ObservationSetWithObservations = client.get_calibration_set()
    quality_metric_set: ObservationSetWithObservations = client.get_quality_metric_set(
        calibration_set.observation_set_id
    )

    operation_errors: dict[str, float] = {}

    for observation in quality_metric_set.observations:
        if "qndness" in observation.dut_field:
            continue

        if ".fidelity" in observation.dut_field:
            operation_name: str = observation.dut_field.split(".")[2]

            if operation_name not in ["prx", "measure", "move", "cz"]:
                continue
            operation_target = observation.dut_field.split(".")[-2]

            operation_errors[f"{operation_name}_{operation_target}"] = 1 - observation.value

    return operation_errors


class IQMStarCostEvaluator:
    """TODO(TR): Docstring this

    .. note::
        This is a simplistic version of the cost evaluator.
    """

    def __init__(self, backend: IQMBackend, circuit: QuantumCircuit) -> None:
        """TODO(TR): Docstring"""

        if not backend.has_resonators():
            raise ValueError(f"Expected a backend with a central resonator. Got {backend.name}.")

        self.backend: IQMBackend = backend
        self.circuit: QuantumCircuit = circuit
        self.operation_errors: dict[str, float] = get_operation_errors(backend.name)

        for k, v in self.operation_errors.items():
            print(f"{k}: {v}")

    def _compile_circuit_for_layout(self, layout: list[int]) -> QuantumCircuit:
        """TODO(TR): Docstring"""
        # Adds correct virtual->physical qubit mapping
        compiled_qc = transpile_to_IQM(
            self.circuit,
            backend=self.backend,
            initial_layout=layout,
            perform_move_routing=False,
        )

        # Adds move gates
        compiled_qc = transpile(compiled_qc, backend=self.backend)

        return compiled_qc

    def _compute_circuit_cost(self, circuit: QuantumCircuit) -> float:
        """TODO(TR): Docstring"""
        circuit_cost: float = 0

        for instruction in circuit.data:
            errors_dict_key: str = instruction[0].name

            if errors_dict_key == "r":
                errors_dict_key = "prx"  # prx gate in IQM is r gate in qiskit

            for component in instruction[1]:
                bit_location = circuit.find_bit(component)
                errors_dict_key += f"_{self.backend.index_to_qubit_name(bit_location.index)}_"

            errors_dict_key = errors_dict_key[:-1]  # Remove last "_"

            circuit_cost += self.operation_errors[errors_dict_key]

        return circuit_cost

    def get_top_layouts(self, n_layouts: int) -> list[tuple[list[int], float]]:
        """TODO(TR): Docstring"""
        layouts: list[list[int]] = []

        n_qubits: int = self.circuit.num_qubits
        qubit_indices: list[int] = list(range(self.backend.num_qubits))
        # This is star topology, so each qubit is connected with each other qubit via the central resonator. We can
        # use that fact for the initial selection of the layouts.
        # Remember that order DOES matter, as qubits have different responsibilities and undergo different evolutions.
        for layout in tqdm(permutations(qubit_indices, n_qubits)):
            compiled_qc: QuantumCircuit = self._compile_circuit_for_layout(layout)
            circuit_cost = self._compute_circuit_cost(compiled_qc)
            layouts.append((layout, circuit_cost))
            # print(circuit_cost)

        layouts = sorted(layouts, key=lambda x: x[1])
        return layouts[:n_layouts]


def get_circuit() -> QuantumCircuit:
    """TODO(TR): Docstring"""
    qubits_list: list[list[int]] = [[1, 0, 2]]
    job: LGACZ2 = LGACZ2()
    job.n_repetitions = 1
    job.add_test_circuits(qubits_list, 0.1)
    return job.circuits[0]  # Do not transpile it, because it causes problems with "move" gate later!


def main() -> None:
    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
    )
    backend: IQMBackend = provider.get_backend()

    n_best_layouts: int = 10
    circuit: QuantumCircuit = get_circuit()

    cost_evaluator: IQMStarCostEvaluator = IQMStarCostEvaluator(backend, circuit)

    best_layouts: list[list[int]] = cost_evaluator.get_top_layouts(n_best_layouts)

    for layout in best_layouts:
        print(layout)


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
    circuit: QuantumCircuit = get_circuit()

    layouts, cost = CostEvaluator(backend=backend, quantum_circuit=circuit).get_top_layouts(num_layouts=n_best_layouts)
    print(f"Top {n_best_layouts} qiskit layouts and their costs:")
    for layout, c in zip(layouts[:n_best_layouts], cost[:n_best_layouts]):
        print(f"Layout: {layout}, Cost: {c * 100:.2f}%")


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
