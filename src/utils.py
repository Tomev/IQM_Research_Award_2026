"""
Utility module for handling general-purpose handling of quantum devices and circuits.
"""

from iqm.qiskit_iqm import IQMBackend, transpile_to_IQM
from qiskit import transpile
from qiskit.circuit.quantumcircuit import QuantumCircuit


def star_device_transpile(circuit: QuantumCircuit, backend: IQMBackend, layout: list[int]) -> QuantumCircuit:
    """Compiles the quantum circuit for a given qubit layout and backend.

    Two transpilation steps are required: first to apply the virtual-to-physical qubit mapping,
    and second to add move gates necessary for the star topology device. Move gates are essential
    for accurately simulating the behavior of the quantum hardware and computing errors more precisely.

    Args:
        circuit: The quantum circuit to be transpiled.
        backend: The IQM backend to target during transpilation.
        layout: A list of integers representing the virtual-to-physical qubit mapping.

    Returns:
        The transpiled quantum circuit with move gates added for the star topology device.
    """
    # Step 1: Adds correct virtual->physical qubit mapping.
    compiled_qc: QuantumCircuit = transpile_to_IQM(
        circuit,
        backend=backend,
        initial_layout=layout,
        perform_move_routing=False,
    )

    # Step 2: Adds move gates.
    compiled_qc = transpile(compiled_qc, backend=backend)

    return compiled_qc
