"""
Utility module for handling general-purpose handling of quantum devices and circuits.
"""

import ast
import json
import os
from datetime import datetime
from typing import Any

from iqm.qiskit_iqm import IQMBackend, transpile_to_IQM
from iqm.qiskit_iqm.iqm_provider import IQMProvider
from qiskit import transpile
from qiskit.circuit.quantumcircuit import QuantumCircuit

from src.jobs import LGACZ2
from src.simulator import download_system_configuration_json

N_REPETITIONS: int = 10
NOW: str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
RESULTS_FOLDER_NAME: str = "./data"


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


def get_backend(backend_name: str | None) -> IQMBackend:
    """
    Get the quantum backend from the IQM provider.

    Returns:
        An instance of :class:`IQMBackendBase` representing the quantum backend.

    Raises:
        EnvironmentError: If the required environment variables (`IQM_PROVIDER` or `IQM_COMPUTER`)
                          are not set.
    """
    if not backend_name:
        backend_name = os.environ["IQM_COMPUTER"]

    return IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=backend_name,
    ).get_backend()


def gather_jobs(jobs_summary_path: str) -> None:
    """Gathers jobs from the quantum device based on a summary file.

    Reads a summary file containing job information, retrieves the corresponding jobs
    from the quantum backend, and saves their results to disk in the expected format.

    Args:
        jobs_summary_path: The file path to the CSV summary file containing job IDs
                           and other metadata.
    """
    print(f"{datetime.now()}: Getting backend...")
    backend: IQMBackend = get_backend()
    print(f"{datetime.now()}: Downloading jobs...")
    jobs: list[LGACZ2] = download_jobs(extract_job_summaries(jobs_summary_path), backend)
    zip_file_name: str = f"{NOW}_iqm_lg_real_{backend.name}_results"

    print(f"{datetime.now()}: Saving jobs...")
    for i, job in enumerate(jobs):
        print(f"\t {i + 1}/{len(jobs)}...")
        file_name: str = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
        job.save_to_file(file_name, f"{RESULTS_FOLDER_NAME}/{zip_file_name}")


def extract_job_summaries(jobs_summary_path: str) -> list[tuple[str, list[list[int]]]]:
    """Extracts job IDs and their corresponding steering bits order from a LG jobs summary file.

    Reads a CSV file containing job metadata, specifically extracting job IDs and the steering bits order associated
    with each job. The steering bits orders are stored as nested lists of integers.

    Args:
        jobs_summary_path: The file path to the CSV summary file containing job IDs and other metadata.

    Returns:
        A list of tuples, where each tuple contains a job ID (str) and steering bit order for the job (list[list[int]]).
    """
    print(f"{datetime.now()}: Extracting job ids...")
    job_summaries: list[tuple[str, list[list[int]]]] = []

    print(f"{datetime.now()}: Got...")
    with open(jobs_summary_path, "r") as f:
        f.readline()  # Skip headers
        line: str = f.readline()

        while line:
            job_summaries.append((line.split(",")[1], ast.literal_eval(line.split('"')[1])))
            print(f"\t{job_summaries[-1][0]}")
            line = f.readline()

    return job_summaries


def download_jobs(job_summaries: list[tuple[str, list[list[int]]]], backend: IQMBackend) -> list[LGACZ2]:
    """
    Downloads jobs from the quantum backend based on the provided job summaries.

    Iterates over the list of job summaries, retrieves each job from the backend,
    and initializes an instance of the :class:`LGACZ2` class with the corresponding
    job data and settings.

    Args:
        job_summaries: A list of tuples, each containing a job ID (str) and the
                       steering bit order (list[list[int]]) for that job.
        backend: The :class:`IQMBackend` instance used to retrieve the jobs from
                 the quantum backend.

    Returns:
        A list of :class:`LGACZ2` instances, each populated with the data from
        the corresponding job retrieved from the backend.
    """
    jobs: list[LGACZ2] = []

    print(f"{datetime.now()}: Retrieved job...")
    for job_summary in job_summaries:
        jobs.append(LGACZ2())
        jobs[-1].n_repetitions = N_REPETITIONS
        jobs[-1].add_test_circuits([[0, 1, 2]], 0.1)
        jobs[-1].indices_list = job_summary[1]
        jobs[-1].queued_job = backend.retrieve_job(job_summary[0])

    return jobs


def get_configuration_dicts(system_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """TODO(TR): Docstring"""
    cd_path, qd_path = download_system_configuration_json(system_name)

    print("Get quality dict...")
    with open(qd_path, "r") as f:
        qd: dict = json.load(f)
    print("Get calibration dict...")
    with open(cd_path, "r") as f:
        cd: dict = json.load(f)

    return cd, qd
