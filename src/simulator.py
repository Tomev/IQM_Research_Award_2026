"""
A module containing functionalities for IQM `sirius` simulator creation.

This module provides tools to create fake IQM backends for quantum simulation purposes. It includes functions to
retrieve quantum architectures, error profiles, and other necessary parameters from IQM systems. These can be used to
construct simulators that mimic the behavior of real IQM quantum computers, such as (but not limited to) the `sirius`
system.
"""

import os
from collections import defaultdict
from typing import Literal

from iqm.iqm_client import IQMClient, StaticQuantumArchitecture
from iqm.qiskit_iqm import IQMBackend, IQMProvider
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import (
    IQMErrorProfile,
    IQMFakeBackend,
)
from iqm.station_control.interface.models import ObservationSetWithObservations
from numpy import average

TimeType = Literal["t1_time", "t2_time"]


def get_architecture(system_name: str) -> StaticQuantumArchitecture:
    """Returns the static quantum architecture for the given system.

    This function constructs a :class:`StaticQuantumArchitecture` object based on the
    specified system name, using the backend information retrieved from the IQM provider.

    Args:
        system_name: The name of the quantum system for which the architecture is to be retrieved.

    Returns:
        StaticQuantumArchitecture: The static quantum architecture for the given system.
    """

    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=system_name,
    )
    backend: IQMBackend = provider.get_backend()

    return StaticQuantumArchitecture(
        dut_label=f"Fake{system_name.capitalize()}",
        qubits=backend.architecture.qubits,
        computational_resonators=backend.architecture.computational_resonators,
        connectivity=get_coupling_map(backend),
    )


def get_coupling_map(backend: IQMBackend) -> list[tuple[str, str]]:
    """Constructs the coupling map for the given backend based on the device topology.

    For star topology devices, the coupling map connects the central computational resonator to all qubits.
    For crystal topology devices, the coupling map is constructed from the backend's coupling map, which defines
    direct qubit-to-qubit connections. Qubit names are adjusted to match the convention used on IQM devices,
    where qubit identifiers start with 'QB' followed with indices, starting from 1.

    .. note::
        Perhaps we can use `backend.coupling_map` as is. That's, however, not how it is done in `FakeVLQ`.

    .. warning::
        This will fail in the future, for the constellation-type devices.
    """
    coupling_map: list[tuple[str, str]] = []

    if backend.has_resonators():
        # If it's a star, then connect resonator with every qubit.
        resonator_name: str = backend.architecture.computational_resonators[0]
        for qubit in backend.architecture.qubits:
            coupling_map.append((resonator_name, qubit))
    else:
        # If it's a crystal, just construct the connectivity map from the coupling map extracted from backend.
        for connection in backend.coupling_map:
            # Qubit names on IQM devices start with QB and are numbered from 1 onwards. Contrary to indices, which
            # start at 0. Coupling map stores indices, so we will add one to every index.
            coupling_map.append((f"QB{connection[0] + 1}", f"QB{connection[1] + 1}"))

    return coupling_map


def get_error_profile(system_name: str) -> IQMErrorProfile:
    """Returns the error profile for the given system.

    This function retrieves the error profile parameters, from the IQM server using the specified system name. It
    constructs an :class:`IQMErrorProfile` object containing these parameters, which are essential for simulating the
    quantum system with noise.

    Args:
        system_name: The name of the quantum system for which the error profile is to be retrieved.

    Returns:
        IQMErrorProfile: The error profile for the given system.
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

    backend_gates: dict[str, list[str]] = get_gates(backend)

    t1: dict[str, float] = get_ts(quality_metric_set, "t1_time")

    return IQMErrorProfile(
        t1s=t1,
        t2s=ensure_t2_correct(t1, get_ts(quality_metric_set, "t2_time")),
        single_qubit_gate_depolarizing_error_parameters=compute_single_qubit_gates_depolarizing_error_parameters(
            quality_metric_set, backend_gates["1q"]
        ),
        two_qubit_gate_depolarizing_error_parameters=compute_two_qubit_gates_depolarizing_error_parameters(
            quality_metric_set, backend_gates["2q"]
        ),
        single_qubit_gate_durations=get_gates_duration(calibration_set, backend_gates["1q"]),
        two_qubit_gate_durations=get_gates_duration(calibration_set, backend_gates["2q"]),
        readout_errors=get_readout_errors(quality_metric_set),
    )


def get_ts(quality_metric_set: ObservationSetWithObservations, time_type: TimeType) -> dict[str, float]:
    """Returns the T1 or T2 times for each component (qubit / resonator) from the quality metric set.

    This function processes the observations in the quality metric set and extracts the T1 or T2 times based on the
    specified time type. It maps each observation to a component name and converts the values from seconds to
    nanoseconds, as expected by the `IQMErrorProfile`.

    Args:
        quality_metric_set:
            The set of observations containing quality metrics.
        time_type:
            The type of time to extract, either "t1_time" or "t2_time".

    Returns:
        dict[str, float]: A dictionary mapping component names to their corresponding T1 or T2 times in nanoseconds.
    """
    ts: dict[str, float] = {}

    for observation in quality_metric_set.observations:
        if time_type in observation.dut_field:
            component_name: str = observation.dut_field.split(".")[-2]
            ts[component_name] = observation.value * 1e9  # seconds to nano seconds
            print(f"{observation.dut_field}: {observation.value * 1e9}")

    return ts


def ensure_t2_correct(t1: dict[str, float], t2: dict[str, float]) -> dict[str, float]:
    """Ensures T2 times are within valid bounds relative to T1 times.

    In some of the calibration data, we encountered:

    qiskit_aer.noise.noiseerror.NoiseError: 'Invalid T_2 relaxation time parameter: T_2 greater than 2 * T_1.'

    which made it impossible to create fake devices. To prevent this from halting experiments, this function ensures
    that T2 times do not exceed twice the corresponding T1 times for each component.

    Args:
        t1: A dictionary mapping component names to their T1 times in nanoseconds.
        t2: A dictionary mapping component names to their T2 times in nanoseconds.

    Returns:
        dict[str, float]: A dictionary with T2 times adjusted to be no greater than 2 * T1 for each component.
    """
    for k in t2.keys():
        t2[k] = min(t2[k], 2 * t1[k])

    return t2


def get_gates(backend: IQMBackend) -> dict[str, list[str]]:
    """Returns a dictionary mapping backend-extracted gate info to lists of gate names supported by the backend.

    This function processes the gate information from the backend's architecture and categorizes the gates
    into single-qubit (1q) and two-qubit (2q) operations based on the number of `loci` specified in the gate data.

    .. note::
        The list of valid gates was provided by the `IQMErrorProfile` error.
    """
    valid_gates: list[str] = ["move", "prx", "cc_prx", "cz"]

    backend_gates: dict[str, list[str]] = {"1q": [], "2q": []}

    for gate_name, gate_data in backend.architecture.gates.items():
        if gate_name not in valid_gates:  # Skip unavailable gates
            continue

        backend_gates[f"{len(gate_data.loci[-1])}q"].append(gate_name)

    return backend_gates


def compute_single_qubit_gates_depolarizing_error_parameters(
    quality_metric_set: ObservationSetWithObservations, gates: list[str]
) -> dict[str, dict[str, float]]:
    """Computes depolarizing error parameters for single-qubit gates.

    This function calculates the depolarizing error parameter for each single-qubit gate based on the fidelity values
    obtained from the quality metric set of observations.

    .. note::
        Depolarizing error parameter can be obtained from the fidelity. In the case of 1-qubit gates it's given by

        .. math::

            p_{depolarization}(F) = 2 * (1 - F),

        where :math:`F` is the fidelity.
    """
    depolarizing_error_parameters: dict[str, dict[str, float]] = defaultdict(lambda: {})

    for observation in quality_metric_set.observations:
        if ".fidelity" in observation.dut_field:
            gate_name: str = observation.dut_field.split(".")[2]

            if gate_name not in gates:  # Omit the gates that are of no interest to us.
                continue

            component_name: str = observation.dut_field.split(".")[-2]
            depolarizing_error_parameters[gate_name][component_name] = 2 * (1 - observation.value)

    return depolarizing_error_parameters


def compute_two_qubit_gates_depolarizing_error_parameters(
    quality_metric_set: ObservationSetWithObservations, gates: list[str]
) -> dict[str, dict[tuple[str, str], float]]:
    """Computes depolarizing error parameters for two-qubit gates.

    This function calculates the depolarizing error parameter for each two-qubit gate based on the fidelity values
    obtained from the quality metric set of observations.

    .. note::
        Depolarizing error parameter can be obtained from the fidelity. In the case of 2-qubit gates it's given by

        .. math::

            p_{depolarization}(F) = 4/3 * (1 - F),

        where :math:`F` is the fidelity.
    """

    depolarizing_error_parameters: dict[str, dict[tuple[str, str], float]] = defaultdict(lambda: {})

    for observation in quality_metric_set.observations:
        if ".fidelity" in observation.dut_field:
            gate_name: str = observation.dut_field.split(".")[2]

            if gate_name not in gates:  # Omit the gates that are of no interest to us.
                continue

            operation_components: list[str] = observation.dut_field.split(".")[-2].split("__")
            inner_key: tuple[str, str] = (operation_components[0], operation_components[1])
            depolarizing_error_parameters[gate_name][inner_key] = 4 / 3 * (1 - observation.value)

    return depolarizing_error_parameters


def get_gates_duration(calibration_set: ObservationSetWithObservations, gates: list[str]) -> dict[str, float]:
    """Returns the average gate durations in nanoseconds for each gate type.

    This function processes the calibration set observations to extract the durations of single-qubit and two-qubit
    gates. For each gate type, it computes the average duration across all qubits or qubit pairs and returns the
    result in nanoseconds.

    .. note::
        In `FakeVLQ` gate duration is a single number. In publicly defined IQM devices, the durations are defined for
        each qubit / component (pair), but seem to be the same for every qubit (qubit_pair). Just in case, we compute
        and return the average for each gate.
    """
    gates_duration: dict[str, list[float]] = defaultdict(lambda: [])

    for observation in calibration_set.observations:
        if "duration" in observation.dut_field:
            gate_name: str = observation.dut_field.split(".")[1]

            if gate_name not in gates:  # Skip gates that are of no interest.
                continue

            gates_duration[gate_name].append(observation.value)

    return {k: average(v) * 1e9 for k, v in gates_duration.items()}  # convert seconds to nano seconds


def get_readout_errors(
    quality_metric_set: ObservationSetWithObservations,
) -> dict[str, dict[str, float]]:
    """Returns the readout error probabilities for each component (qubit / resonator).

    This function processes the observations in the quality metric set and extracts the readout error probabilities
    for each component. It maps each observation to a component name and collects the error probabilities for
    both :math:`|0\\rangle \\rightarrow |1\\rangle` and :math:`|1\\rangle \\rightarrow |0\\rangle` transitions.

    Args:
        quality_metric_set:
            The set of observations containing quality metrics.

    Returns:
        dict[str, dict[str, float]]: A dictionary mapping component names to their corresponding readout error
        probabilities. Each component has two entries: "0" for :math:`|0\\rangle \\rightarrow |1\\rangle`
        and "1" for :math:`|1\\rangle \\rightarrow |0\\rangle` transitions.
    """
    readout_errors: dict[str, dict[str, float]] = defaultdict(lambda: {})

    for observation in quality_metric_set.observations:
        if "error_0_to_1" in observation.dut_field:
            component_name: str = observation.dut_field.split(".")[-2]
            readout_errors[component_name]["0"] = observation.value

        if "error_1_to_0" in observation.dut_field:
            component_name: str = observation.dut_field.split(".")[-2]
            readout_errors[component_name]["1"] = observation.value

    return readout_errors


def FakeFromBackend(system_name: str) -> IQMFakeBackend:
    """Creates a fake IQM backend simulator for the specified system.

    This function constructs an :class:`IQMFakeBackend` object using the static quantum architecture and error profile
    of the specified system. The resulting backend can be used for simulations that mimic the behavior of the real IQM
    quantum computer.

    Args:
        system_name: The name of the quantum system for which the fake backend is to be created.

    Returns:
        IQMFakeBackend: A fake backend simulator for the specified system.
    """

    return IQMFakeBackend(
        get_architecture(system_name),
        get_error_profile(system_name),
        name=f"Fake{system_name.capitalize()}",
    )


def FakeSirius() -> IQMFakeBackend:
    """Creates a fake IQM backend simulator for the Sirius quantum system.

    This function constructs an :class:`IQMFakeBackend` object using the static quantum architecture and error profile
    specific to the `sirius` system. The resulting backend can be used for simulations that mimic the behavior of the
    real IQM `sirius` quantum computer.

    Returns:
        IQMFakeBackend: A fake backend simulator for the `sirius` system.
    """
    return FakeFromBackend("sirius")
