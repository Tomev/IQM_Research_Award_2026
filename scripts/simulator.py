"""
A module containing functionalities for IQM `siruis` simulator creation. It's actually more general than that.
"""

import os

from iqm.iqm_client import IQMClient, StaticQuantumArchitecture
from iqm.qiskit_iqm import IQMBackend, IQMProvider
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import (
    IQMErrorProfile,
    IQMFakeBackend,
)
from iqm.station_control.interface.models import ObservationSetWithObservations


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
    raise NotImplementedError


def get_t1s(quality_metrics: ObservationSetWithObservations) -> dict[str, float]:
    """TODO(TR): Docstring"""
    t1s: dict[str, float] = {}
    raise NotImplementedError


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

    calibration_set: ObservationSetWithObservations = client.get_calibration_set()
    quality_metric_set: ObservationSetWithObservations = client.get_quality_metric_set(
        calibration_set.observation_set_id
    )
    # print(calibration_set.observations)
    # print(quality_metric_set)

    for x in quality_metric_set.observations:
        if "t1" in x.dut_field:
            print(f"\n{x}\n")


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
