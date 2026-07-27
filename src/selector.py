"""
This module provides tools for evaluating the cost of quantum circuits on star-shaped topology backends using operation
errors. It includes a function for retrieving operation errors from a quantum system, a class for evaluating the cost of
circuits based on these errors, and helper methods for compiling circuits and computing their costs.

The primary use case is to find optimal qubit layouts that minimize the total error of a quantum circuit, based on the
errors of individual quantum operations such as PRX, measure, move, and CZ.

Key components:
- :func:`get_operation_errors`: Retrieves operation errors for a given quantum system.
- :class:`IQMStarCostEvaluator`: Evaluates the cost of a quantum circuit based on operation errors.
"""

import os
from itertools import permutations

from iqm.iqm_client import IQMClient
from iqm.qiskit_iqm import IQMBackend
from iqm.station_control.interface.models import ObservationSetWithObservations
from qiskit.circuit.quantumcircuit import QuantumCircuit
from tqdm import tqdm

from src.utils import star_device_transpile


def get_operation_errors(system_name: str) -> dict[str, float]:
    """Retrieves operation errors for a given quantum system.

    The errors are calculated as (1 - fidelity), where fidelity represents the performance of quantum
    operations such as PRX, measure, move, and CZ.
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
    """A cost evaluator for star-shaped topology backends using operation errors.

    This evaluator computes the cost of a quantum circuit based on the errors of individual operations.
    It is a simplistic version of the cost evaluator, as it only considers operation errors to find the best layouts,
    without incorporating more advanced factors such as gate durations, crosstalk, or other hardware-specific
    constraints.

    .. note::
        This is a simplistic version of the cost evaluator. The simplicity is the result of only using operation errors
        to find the best layouts. This approach may not account for all hardware-specific factors.
    """

    def __init__(self, backend: IQMBackend, circuit: QuantumCircuit) -> None:
        """Initializes the cost evaluator for a star-shaped topology backend.

        This evaluator is designed to work specifically with backends that have a star-shaped topology,
        where all qubits are connected through a central resonator.

        Args:
            backend:
                The quantum backend to use. Must have a star-shaped topology with a central resonator.
                If not, a ValueError is raised.
            circuit:
                The quantum circuit for which the cost is to be evaluated.

        Raises:
            ValueError:
                If the backend does not have a central resonator, indicating that it is not compatible
                with the star-shaped topology required by this evaluator.
        """

        if not backend.has_resonators():
            raise ValueError(f"Expected a backend with a central resonator. Got {backend.name}.")

        self.backend: IQMBackend = backend
        self.circuit: QuantumCircuit = circuit
        self.operation_errors: dict[str, float] = get_operation_errors(backend.name)

    def _compute_circuit_cost(self, circuit: QuantumCircuit) -> float:
        """Computes the total cost of a quantum circuit based on operation errors.

        The cost is calculated by summing the errors of each operation in the circuit. Each operation's
        error is retrieved from the :attr:`operation_errors` dictionary, which maps operation names and
        qubit (resonator / pair) targets to their respective error values.

        Args:
            circuit: The quantum circuit for which the cost is to be computed.

        Returns:
            float: The total cost of the circuit, representing the sum of errors.
        """
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

    def get_top_layouts(self, n_layouts: int) -> list[tuple[tuple[int, ...], float]]:
        """Returns the top layouts with the lowest circuit cost.

        The layouts are generated by permuting all possible qubit indices and evaluating the
        compiled circuit cost for each layout. The resulting list is sorted by cost and
        limited to the specified number of best layouts.

        Args:
            n_layouts: The number of top layouts to return.

        Returns:
            list[tuple[tuple[int, ...], float]]: A list of tuples, where each tuple contains
                a layout (as a permutation of qubit indices) and its corresponding circuit cost.
        """
        layouts: list[tuple[tuple[int, ...], float]] = []

        n_qubits: int = self.circuit.num_qubits
        qubit_indices: list[int] = list(range(self.backend.num_qubits))
        # This is star topology, so each qubit is connected with each other qubit via the central resonator. We can
        # use that fact for the initial selection of the layouts.
        # Remember that order DOES matter, as qubits have different responsibilities and undergo different evolutions.
        for layout in tqdm(permutations(qubit_indices, n_qubits)):
            compiled_qc: QuantumCircuit = star_device_transpile(self.circuit, self.backend, layout)
            circuit_cost: float = self._compute_circuit_cost(compiled_qc)
            layouts.append((layout, circuit_cost))

        layouts = sorted(layouts, key=lambda x: x[1])
        return layouts[:n_layouts]
