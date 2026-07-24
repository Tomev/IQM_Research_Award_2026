"""
A module containing functionalities for IQM `siruis` simulator creation. It's actually more general than that.
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

    calibration_set: ObservationSetWithObservations = client.get_calibration_set()
    quality_metric_set: ObservationSetWithObservations = client.get_quality_metric_set(
        calibration_set.observation_set_id
    )
    return IQMErrorProfile(
        t1s=get_ts(quality_metric_set, "t1"),
        t2s=get_ts(quality_metric_set, "t2"),
        single_qubit_gate_depolarizing_error_parameters={},
        two_qubit_gate_depolarizing_error_parameters={},
        single_qubit_gate_durations={},
        two_qubit_gate_durations={},
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

    print(get_readout_errors(quality_metric_set))
    return

    # for k, v in backend.architecture.gates.items():
    #    print(f"\n{k}: {v}")

    value_sought: str = "error_1_to_0"

    """
    for observation in calibration_set.observations:
        if value_sought in observation.dut_field:
            print(f"\n{observation}\n")
    """

    for observation in quality_metric_set.observations:
        if value_sought in observation.dut_field:
            print(f"\n{observation}\n")

    # print(get_ts(quality_metric_set, "t1"))
    # print(get_ts(quality_metric_set, "t2"))


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
