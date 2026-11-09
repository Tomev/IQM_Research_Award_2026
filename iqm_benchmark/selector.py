"""
This module provides tools for evaluating the cost of quantum circuits on star-shaped topology backends using operation
errors. It includes a function for retrieving operation errors from a quantum system, a class for evaluating the cost of
circuits based on these errors, and helper methods for compiling circuits and computing their costs.

The primary use case is to find optimal qubit layouts that minimize the total error of a quantum circuit, based on the
errors of individual quantum operations such as PRX, measure, move, and CZ.

Key components:
- :func:`get_operation_errors`: Retrieves operation errors from the configuration dicts of a quantum system.
- :class:`IQMStarCostEvaluator`: Evaluates the cost of a quantum circuit based on operation errors.
"""

from itertools import permutations
from typing import Any

from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMFakeBackend
from qiskit.circuit.quantumcircuit import QuantumCircuit
from tqdm import tqdm

from iqm_benchmark.simulator import FakeFromDicts
from iqm_benchmark.utils import star_device_transpile

# The operations that contribute to the circuit cost.
COST_OPERATIONS: tuple[str, ...] = ("prx", "measure", "move", "cz")


def get_operation_errors(calibration_dict: dict[str, Any], quality_dict: dict[str, Any]) -> dict[str, float]:
    """Retrieves operation errors from the configuration dicts of a quantum system.

    The errors are calculated as (1 - fidelity), where fidelity represents the performance of quantum
    operations such as PRX, measure, move, and CZ.

    Args:
        calibration_dict:
            A `dict` containing the calibration set. Not used at the moment, as all the fidelities are stored in the
            quality metrics. It is accepted so that the function takes the same configuration as the simulator.
        quality_dict:
            A `dict` containing the quality metrics, with fidelities stored under the "observations" key.

    Returns:
        dict[str, float]: The errors, keyed by `<operation name>_<operation target>`, e.g. `cz_QB1__COMPR1`.
    """
    operation_errors: dict[str, float] = {}

    for observation in quality_dict["observations"]:
        dut_field: str = observation["dut_field"]

        if "qndness" in dut_field:
            continue

        if ".fidelity" in dut_field:
            operation_name: str = dut_field.split(".")[2]

            if operation_name not in COST_OPERATIONS:
                continue
            operation_target: str = dut_field.split(".")[-2]

            operation_errors[f"{operation_name}_{operation_target}"] = 1 - observation["value"]

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

    def __init__(
        self,
        architecture_dict: dict[str, Any],
        calibration_dict: dict[str, Any],
        quality_dict: dict[str, Any],
        circuit: QuantumCircuit,
    ) -> None:
        """Initializes the cost evaluator for a star-shaped topology backend.

        This evaluator is designed to work specifically with backends that have a star-shaped topology,
        where all qubits are connected through a central resonator. The backend is not passed directly. Instead, a fake
        one is built from the configuration dicts, so that the evaluator does not need access to the device.

        Args:
            architecture_dict:
                A `dict` describing the architecture (qubits, computational resonators and gates). Must describe a
                star-shaped topology with a central resonator. If not, a ValueError is raised.
            calibration_dict:
                A `dict` containing the calibration set.
            quality_dict:
                A `dict` containing the quality metrics.
            circuit:
                The quantum circuit for which the cost is to be evaluated.

        Raises:
            ValueError:
                If the architecture does not have a central resonator, indicating that it is not compatible
                with the star-shaped topology required by this evaluator.
        """
        if not architecture_dict["computational_resonators"]:
            raise ValueError("Expected an architecture with a central resonator. Got one without resonators.")

        self.backend: IQMFakeBackend = FakeFromDicts(architecture_dict, calibration_dict, quality_dict)
        self.circuit: QuantumCircuit = circuit
        self.operation_errors: dict[str, float] = get_operation_errors(calibration_dict, quality_dict)

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
