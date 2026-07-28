"""TODO(TR): Docstring"""

import os
from datetime import datetime

from iqm.pulla.pulla import Pulla, PullaStash
from iqm.pulla.utils_qiskit import qiskit_to_pulla, sweep_job_to_qiskit
from iqm.pulse.playlist.visualisation.base import inspect_playlist
from iqm.qiskit_iqm import IQMBackend
from qiskit import QuantumCircuit, visualization
from qiskit.compiler import transpile

from src.jobs import LGACZ2, Job
from src.pipelines import prepare_lg_jobs
from src.utils import get_backend


def compute_cz_amplitude_calibration_override(pulla: Pulla, amplitude_multiplier: float = 0.8) -> dict[str, float]:
    """TODO(TR): Docstring"""

    calibration_stash: PullaStash = pulla.get_calibration_stash()
    calibration_override: dict[str, float] = {}

    for k, v in calibration_stash.observations.items():
        if "amplitude" in k and "cz" in k:
            calibration_override[k] = v.value * amplitude_multiplier
            # print(f"{k}: {v.value} vs {calibration_override[k]}")

    return calibration_override


def main() -> None:
    print(f"{datetime.now()}: Getting backend...")
    backend: IQMBackend = get_backend()
    print(f"{datetime.now()}: Preparing jobs...")
    qubit_layouts: list[tuple[int, ...]] = [(4, 5, 6)]  # Best tripled. Used in gates experiment.
    lg_jobs: list[Job] = prepare_lg_jobs(qubit_layouts, backend)
    print(lg_jobs[0].circuits[0])
    print(f"{datetime.now()}: Getting pulla...")
    # Define the standard compiler that loads the default calibration set as its initial operating point.
    pulla: Pulla = Pulla(os.environ["IQM_PROVIDER"], quantum_computer=os.environ["IQM_COMPUTER"])

    calibration_override: dict[str, float] = compute_cz_amplitude_calibration_override(pulla)

    print(f"{datetime.now()}: Preparing pulla circuits and compiler...")
    circuits, compiler = qiskit_to_pulla(pulla, backend, lg_jobs[0].circuits)

    print(f"{datetime.now()}: Getting pulla compiler settings...")
    # Generate the settings for an empty list of circuits
    settings = compiler.get_settings(circuits=circuits)

    for key, v in calibration_override.items():
        settings[key] = v

    print(f"{datetime.now()}: Compiling the job definition...")
    # Compile the circuit into a job definition containing a playlist of instruction schedules.
    playlist, context = compiler.compile(circuits, settings=settings)


if __name__ == "__main__":
    print(f"{datetime.now()}: Start")
    main()
    print(f"{datetime.now()}: Done")
