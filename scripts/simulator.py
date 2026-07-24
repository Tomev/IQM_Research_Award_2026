"""
A module containing functionalities for IQM `siruis` simulator creation. It p
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

TimeType = Literal["t1", "t2"]

from numpy import average


def get_architecture(system_name: str) -> StaticQuantumArchitecture:
    """TODO(TR): Docstring"""

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
    """TODO(TR): Docstring

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
    """TODO(TR): Docstring"""
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

    return IQMErrorProfile(
        t1s=get_ts(quality_metric_set, "t1"),
        t2s=get_ts(quality_metric_set, "t2"),
        single_qubit_gate_depolarizing_error_parameters={},
        two_qubit_gate_depolarizing_error_parameters={},
        single_qubit_gate_durations=get_gates_duration(
            calibration_set, backend_gates["1q"]
        ),
        two_qubit_gate_durations=get_gates_duration(
            calibration_set, backend_gates["2q"]
        ),
        readout_errors=get_readout_errors(quality_metric_set),
    )


def get_ts(
    quality_metric_set: ObservationSetWithObservations, time_type: TimeType
) -> dict[str, float]:
    """TODO(TR): Docstring"""
    ts: dict[str, float] = {}

    for observation in quality_metric_set.observations:
        if time_type in observation.dut_field:
            component_name: str = observation.dut_field.split(".")[-2]
            ts[component_name] = observation.value * 1e9  # seconds to nano seconds

    return ts


def get_gates(backend: IQMBackend) -> dict[str, list[str]]:
    """TODO(TR): Docstring

    .. warning::
        This method is slightly over the top, returning also measurements and variants of the gates. It, however
        should work with general backend.
    """
    backend_gates: dict[str, list[str]] = {"1q": [], "2q": []}

    for gate_name, gate_data in backend.architecture.gates.items():
        backend_gates[f"{len(gate_data.loci[-1])}q"].append(gate_name)

    return backend_gates


def get_gates_duration(
    calibration_set: ObservationSetWithObservations, gates: list[str]
) -> dict[str, float]:
    """TODO(TR): Docstring

    .. note::
        In FakeVLQ it is a single number. In publicly defined IQM devices, the durations are defined for each qubit
        (qubits pair), but seem to be the same for every qubit (qubit_pair). Just in case, we compute and return the
        average for each gate.
    """
    gates_duration: dict[str, list[float]] = defaultdict(lambda: [])

    for observation in calibration_set.observations:
        if "duration" in observation.dut_field:
            gate_name: str = observation.dut_field.split(".")[1]

            if gate_name not in gates:  # Skip gates that are of no interest.
                continue

            gates_duration[gate_name].append(observation.value)

            # print(f"\n{observation}\n")

    return {
        k: average(v) * 1e9 for k, v in gates_duration.items()
    }  # convert seconds to nano seconds


def get_readout_errors(
    quality_metric_set: ObservationSetWithObservations,
) -> dict[str, dict[str, float]]:
    """TODO(TR): Docstring"""
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
    """TODO(TR): Docstring"""

    return IQMFakeBackend(
        get_architecture(system_name),
        get_error_profile(system_name),
        name=f"Fake{system_name.capitalize()}",
    )


def FakeSirius() -> IQMFakeBackend:
    """TODO(TR): Docstring"""
    return FakeFromBackend("sirius")


def main() -> None:
    """TODO(TR): Docstring"""
    client: IQMClient = IQMClient(
        iqm_server_url=os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],  # sirius
    )

    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
    )

    backend: IQMBackend = provider.get_backend()
    calibration_set: ObservationSetWithObservations = client.get_calibration_set()
    quality_metric_set: ObservationSetWithObservations = client.get_quality_metric_set(
        calibration_set.observation_set_id
    )

    gates: dict[str, list[str]] = get_gates(backend)

    value_sought: str = "fidelity"

    print("\n\nCalibration:")

    for observation in calibration_set.observations:
        if value_sought in observation.dut_field and "QB17" in observation.dut_field:
            print(f"\n{observation}\n")

    print("\n\nQuality:")

    for observation in quality_metric_set.observations:
        if value_sought in observation.dut_field and "QB17" in observation.dut_field:
            print(f"\n{observation}\n")


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
