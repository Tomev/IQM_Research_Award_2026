"""
Utility module for handling general-purpose handling of quantum devices and circuits.
"""

import os

from iqm.qiskit_iqm import IQMBackend, transpile_to_IQM
from iqm.qiskit_iqm.iqm_provider import IQMProvider
from qiskit import transpile
from qiskit.circuit.quantumcircuit import QuantumCircuit

from src.jobs import LGACZ2
from src.pipelines import NOW, RESULTS_FOLDER_NAME


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


def get_backend() -> IQMBackend:
    """
    Get the quantum backend from the IQM provider.

    Returns:
        An instance of :class:`IQMBackendBase` representing the quantum backend.

    Raises:
        EnvironmentError: If the required environment variables (`IQM_PROVIDER` or `IQM_COMPUTER`)
                          are not set.
    """
    return IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
    ).get_backend()


def gather_jobs_from_device(jobs_summary_path: str) -> None:
    """Gathers jobs from the quantum device based on a summary file.

    Reads a summary file containing job information, retrieves the corresponding jobs
    from the quantum backend, and saves their results to disk in the expected format.

    Args:
        jobs_summary_path: The file path to the CSV summary file containing job IDs
                           and other metadata.
    """
    backend: IQMBackend = get_backend()
    jobs: list[LGACZ2] = download_jobs(extract_job_ids(jobs_summary_path), backend)
    zip_file_name: str = f"{NOW}_iqm_lg_real_{backend.name}_results"

    for i, job in enumerate(jobs):
        file_name: str = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
        job.save_to_file(file_name, f"{RESULTS_FOLDER_NAME}/{zip_file_name}")


def extract_job_ids(jobs_summary_path: str) -> list[str]:
    """Extracts job IDs from a summary file.

    Parses a CSV file containing job summaries and extracts the job IDs.

    Args:
        jobs_summary_path: The file path to the CSV summary file containing job information.

    Returns:
        A list of strings, where each string is a job ID extracted from the summary file.
    """
    job_ids: list[str] = []

    with open(jobs_summary_path, "r") as f:
        f.readline()  # Skip headers
        line: str = f.readline()

        while line:
            job_ids.append(line.split(",")[1])

    return job_ids


def download_jobs(job_ids: list[str], backend: IQMBackend) -> list[LGACZ2]:
    """Downloads the results of specified jobs from the quantum backend.

    Retrieves the job results for a list of job IDs and converts them into instances
    of the :class:`LGACZ2` class, which are used for further processing and analysis.

    Args:
        job_ids: A list of strings representing the unique identifiers of the quantum jobs.
        backend: The IQM backend from which the job results will be retrieved.

    Returns:
        A list of :class:`LGACZ2` objects, each containing the results of a corresponding job.
    """
    jobs: list[LGACZ2] = []

    for job_id in job_ids:
        jobs.append(LGACZ2())
        jobs[-1].queued_job = backend.retrieve_job(job_id)

    return jobs
