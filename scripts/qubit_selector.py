"""A module with qubit selector training

.. note::
    IQM Qubit Selector is programmed to work with the crystal topology devices. It
"""

import os
from collections import defaultdict
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

    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=system_name,
    )
    backend: IQMBackend = provider.get_backend()

    calibration_set: ObservationSetWithObservations = client.get_calibration_set()
    quality_metric_set: ObservationSetWithObservations = client.get_quality_metric_set(
        calibration_set.observation_set_id
    )

    operation_errors: dict[str, float] = {}

    for observation in quality_metric_set.observations:
        if "tgss" in observation.dut_field or "qndness" in observation.dut_field:
            continue

        if ".fidelity" in observation.dut_field:
            operation_name: str = observation.dut_field.split(".")[2]

            if operation_name not in ["prx", "measure", "move", "cz"]:
                continue
            operation_target = observation.dut_field.split(".")[-2]
            # print(observation.dut_field)

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
            raise ValueError(f"Expected a backend with a central resonator. Got {backend}.")

        self.backend: IQMBackend = backend
        self.circuit: QuantumCircuit = circuit

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

    def get_top_layouts(self, n_layouts: int) -> list[list[int]]:
        """TODO(TR): Docstring"""
        layouts: list[list[int]] = []

        n_qubits: int = self.circuit.num_qubits
        qubit_indices: list[int] = list(range(self.backend.num_qubits))
        # This is star topology, so each qubit is connected with each other qubit via the central resonator. We can
        # use that fact for the initial selection of the layouts.
        # Remember that order DOES matter, as qubits have different responsibilities and undergo different evolutions.
        initial_layouts = list(permutations(qubit_indices, n_qubits))
        print(len(list(initial_layouts)))

        compiled_qc: QuantumCircuit = self._compile_circuit_for_layout(initial_layouts[-1])
        # print(compiled_qc)
        for instruction in compiled_qc.data:
            print(instruction)

        operation_errors = get_operation_errors(self.backend.name)
        print(operation_errors)

        return layouts


def find_lgi_triplets(backend: IQMBackend) -> list[dict[str, int]]:
    """
    Given the IBM backend, find the qubit triplets for the Laggett-Garg test experiment.
    We require that qubits X, A, B are connected in the following way:

    X -> A

    and

    X -> B,

    where the arrow denotes the direction of the entangling gate.

    :params:
        backend:     IBM backend.

    :return:
        A list of LGI-eligible qubit triplets.
    """
    lgi_triplets: list[dict[str, int]] = []

    coupling_map = backend.coupling_map

    def format_connection(con: list[list[int]]):
        return {"x": con[0][0], "a": con[1][0], "b": con[1][1]}

    for x in tqdm(range(backend.num_qubits)):
        # Find all qubits that x can control.
        connections = find_qubit_connections(backend, x)

        if len(connections) < 2:
            continue

        if len(connections) > 2:
            # Prepare 2-length permutations of the connections.
            connections = list(combinations(connections, 2))
        if len(connections) == 2:
            connections = [connections]  # Hax for more general processing.

        for con in connections:
            lgi_triplets.append(format_connection([[x], con]))

    return lgi_triplets


def find_qubit_connections(backend: IQMBackend, qubit: int) -> list[int]:
    """
    Find all qubits that are connected to the given qubit.

    :params:
        backend:     IBM backend.
        qubit:       The qubit to check connections for.

    :return:
        A list of connections in the backend that qubit controls.
    """
    coupling_map = backend.coupling_map

    return [con[1] for con in coupling_map if con[0] == qubit]


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
    print(best_layouts)


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
