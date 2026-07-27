"""This module contains experimental pipelines for executing quantum jobs on various quantum backends, including
simulated and real quantum devices. The primary goal is to evaluate the performance of quantum circuits under different
qubit layouts and backend conditions. The pipelines support noiseless simulations, noisy simulations using fake
backends, and execution on real quantum hardware. Each pipeline is designed to prepare, run, and save the results of
quantum jobs, enabling analysis of circuit behavior, error rates, and performance metrics.

The module includes functions for selecting optimal qubit layouts, transpiling circuits for specific devices, and
handling job execution and result collection. It is tailored for research and development in quantum computing,
particularly for testing and benchmarking quantum algorithms and hardware."""

import ast
import json
import os
import time
from datetime import datetime

import pandas as pd
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMBackendBase, IQMFakeBackend
from iqm.qiskit_iqm.iqm_provider import IQMBackend, IQMProvider
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit_aer import AerSimulator

from src.jobs import LGACZ2, Job
from src.selector import IQMStarCostEvaluator
from src.simulator import FakeSirius
from src.utils import star_device_transpile

# TODO(TR): Refactor those settings.
# There are 8 angles per layout in the job. This means the number of circuits in a single job is equal to
#   N_CIRCUITS = 8 x N_REPETITIONS
#
# Prefered setup is N_REPETITONS = 10, meaning that we can only handle 1 qubit layout per job. That is because maximal
# number of circuits per job is 100 (on IQM Sirius).
#

N_JOBS_PER_LAYOUT: int = 5
N_REPETITIONS: int = 10
N_SHOTS: int = int(2e4)  # Max number of shots per circuit on IQM Sirius is 20000 (2e4).

### Test setup
# N_JOBS_PER_LAYOUT: int = 1
# N_REPETITIONS = 1
# N_SHOTS: int = int(10e3)

NOW: str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
WAIT_TIME: int = 10  # TODO(TR): Adjust or remove.
RESULTS_FOLDER_NAME: str = "./data"
RESULTS_FILE_NAME: str = "lg_jobs_summary.csv"


Backend = AerSimulator | IQMBackendBase


def find_best_qubit_layouts(backend: IQMFakeBackend, n_layouts: int = 10) -> list[tuple[int, ...]]:
    """
    Find the best qubit layouts for a given quantum circuit based on a cost evaluator.

    Args:
        backend: The quantum backend to use for evaluation.
        n_layouts: The number of top layouts to return.

    Returns:
        A list of the best qubit layouts, each represented as a tuple of integers.

    Raises:
        ValueError: If the backend is not compatible with the evaluator.

    See Also:
        :class:`IQMStarCostEvaluator` for the cost evaluation logic.
    """

    # Create a job for evaluator
    job: LGACZ2 = LGACZ2()
    job.n_repetitions = N_REPETITIONS
    job.add_test_circuits([[0, 1, 2]], 0.1)

    circuit: QuantumCircuit = job.circuits[0]

    evaluator: IQMStarCostEvaluator = IQMStarCostEvaluator(backend, circuit)

    best_layouts: list[tuple[tuple[int, ...], float]] = evaluator.get_top_layouts(n_layouts)

    save_layouts_info(best_layouts)

    return [layout for layout, _ in best_layouts]


def save_layouts_info(layouts: list[tuple[tuple[int, ...], float]]) -> None:
    """
    Save information about qubit layouts and their corresponding costs to a JSON file.

    Args:
        layouts: A list of tuples, where each tuple contains a qubit layout (as a tuple of integers)
                 and its corresponding cost (as a float).
    """
    layouts_info_dict: dict[str, float] = {str(layout): cost for layout, cost in layouts}

    # Save dict to a file
    with open(f"{RESULTS_FOLDER_NAME}/{NOW}_layouts_info.json", "w") as f:
        json.dump(layouts_info_dict, f, indent=4)


def get_layouts_from_layouts_info(info_file_path: str) -> list[tuple[int, ...]]:
    """
    Load qubit layouts from a JSON file containing layout information.

    Args:
        info_file_path: The path to the JSON file containing qubit layout data.

    Returns:
        A list of qubit layouts, each represented as a tuple of integers.

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        json.JSONDecodeError: If the JSON file is malformed.
        ValueError: If the JSON file contains invalid layout data.

    See Also:
        :func:`save_layouts_info` for the corresponding function that saves layout information.
    """
    try:
        with open(info_file_path, "r") as f:
            layouts: dict[str, float] = json.load(f)

        return [ast.literal_eval(key) for key in layouts.keys()]

    except Exception as e:
        print(e)
        print("Returning empty list to trigger automatic best layers search.")
        return []


def prepare_lg_jobs(qubits_lists: list[list[int] | tuple[int, ...]], backend: Backend) -> list[Job]:
    """
    Prepare a list of jobs for execution on a quantum backend, adjusting the qubit layouts for each job.

    Args:
        qubits_lists:
            A list of qubit layouts, where each layout is a list or tuple of integers representing qubit indices.
        backend:
            The quantum backend to use for execution, which can be either an `AerSimulator` or an `IQMFakeBackend`.

    Returns:
        A list of :class:`Job` instances, each containing quantum circuits adapted to the specified qubit layouts.

    Notes:
        For each qubit layout, multiple jobs are created based on the :data:`N_JOBS_PER_LAYOUT` setting.
        If the backend is not an IQMBackendBase (e.g., is AerSimulator), transpilation is skipped.
    """
    jobs: list[Job] = []
    for layout in qubits_lists:
        for _ in range(N_JOBS_PER_LAYOUT):
            job: LGACZ2 = LGACZ2()
            job.n_repetitions = N_REPETITIONS
            job.add_test_circuits([[0, 1, 2]], 0.1)  # Qubits will be adjusted during transpilation.
            jobs.append(job)

            # Transpile the circuits in the job, if needed
            if not issubclass(type(backend), IQMBackendBase):
                print(f"{datetime.now()}: Skipping circuits transpilation for backend {backend.name}.")

                continue  # Skip noiseless sim.

            for i in range(len(jobs[-1].circuits)):
                jobs[-1].circuits[i] = star_device_transpile(jobs[-1].circuits[i], backend, layout)

    return jobs


def run_jobs(jobs: list[Job], backend: Backend) -> None:
    """
    Run a list of quantum jobs on the specified backend and save jobs summary to a CSV file.

    Args:
        jobs:
            A list of :class:`Job` instances to be executed.
        backend:
            The quantum backend to use for execution, which can be either an AerSimulator or an IQMFakeBackend.

    Notes:
        For each job, the job ID and parameters are recorded in a DataFrame and saved to the CSV file
        specified by :data:`RESULTS_FILE_NAME` in the :data:`RESULTS_FOLDER_NAME` directory.
        If an error occurs during job submission, the error is printed and the code waits for a short
        period before continuing. This is to prevent internet connection-related issues during the circuits
        execution on a real hardware.
    """
    job_list_path: str = f"{RESULTS_FOLDER_NAME}/{NOW}_{RESULTS_FILE_NAME}"
    job_list_table: pd.DataFrame = pd.DataFrame()

    for i, job in enumerate(jobs):
        try:
            job.queued_job = backend.run(job.circuits, shots=N_SHOTS)

            print(f"{datetime.now()}: job {i + 1} (of {len(jobs)}) queued")
            job_data: dict = {
                "job_id": job.queued_job.job_id(),
                "pars": job.indices_list,
            }
            job_list_table = pd.concat([job_list_table, pd.DataFrame([job_data])], ignore_index=True)
            job_list_table.to_csv(job_list_path)
        except Exception as alert:
            print(alert)
            time.sleep(WAIT_TIME)


def wait_and_save_results(jobs: list[Job], zip_file_name: str) -> None:
    """
    Wait for all jobs to complete and save their results to CSV files.

    Args:
        jobs:
            A list of :class:`Job` instances whose results need to be saved.
        zip_file_name:
            The name of the ZIP file to which the results will be archived.

    Notes:
        This function continuously checks the status of each job. When a job is completed,
        its results are saved to a CSV file. If a job fails or is cancelled, an error message
        and relevant metrics are printed. The function waits for a short period before checking
        the status again to avoid overwhelming the system.
    """

    results_ready: bool = False

    while not results_ready:
        results_ready = True
        time.sleep(WAIT_TIME)

        for i in range(len(jobs)):
            if jobs[i].update_status():
                print(i + 1, jobs[i].last_status)
                if jobs[i].last_status == "DONE" and not jobs[i].if_saved:
                    file_name: str = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
                    jobs[i].save_to_file(file_name, f"{RESULTS_FOLDER_NAME}/{zip_file_name}")
                elif jobs[i].last_status in ["ERROR", "CANCELLED"]:
                    print(jobs[i].queued_job.error_message())
                    print(jobs[i].queued_job.metrics()["usage"]["quantum_seconds"])

        for job in jobs:
            if job.last_status not in ["ERROR", "CANCELLED", "DONE"]:
                results_ready = False


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


def save_calibration() -> None:
    """
    Save calibration data for the fake device. The fake device is not used in this function, but is only used to for
    it's functionalities of saving the calibration data.

    TODO(TR): Separate calibration saving from fake backends preparation.
    """

    FakeSirius(save_calibration=True)


def noiseless_pipeline() -> None:
    """
    Execute a noiseless simulation pipeline using a quantum simulator backend.

    Notes:
        This function prepares the jobs with a fixed set of qubits, runs them on a noiseless simulator backend,
        and saves the results. The qubit layout used is [1, 0, 2], which is hardcoded for this specific pipeline.
        The results are saved in the directory specified by :data:`RESULTS_FOLDER_NAME` with the filename
        specified by :data:`RESULTS_FILE_NAME`.

    See Also:
        :func:`noisy_pipeline` for the corresponding function that runs noisy simulations.
    """

    print(f"{datetime.now()}: Preparing backend...")
    backend: Backend = AerSimulator()
    print(f"{datetime.now()}: Preparing jobs...")
    # For noiseless simulations we only need one set of qubits.
    jobs: list[Job] = prepare_lg_jobs(qubits_lists=[[1, 0, 2]], backend=backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"{NOW}_iqm_lg_noiseless_results")


def noisy_pipeline(qubits_lists: list[list[int] | tuple[int, ...]]) -> None:
    """
    Execute a noisy simulation pipeline using the specified qubit layouts on a fake quantum backend.

    Args:
        qubits_lists:
            A list of qubit layouts, where each layout is a list or tuple of integers representing qubit indices.
            If empty, the best layouts are automatically determined using :func:`find_best_qubit_layouts`.

    Notes:
        This function prepares the jobs with the specified qubit layouts, runs them on a fake noisy backend,
        and saves the results. If no layouts are provided, the function first identifies the best layouts
        based on the cost evaluator before proceeding with job execution.

    See Also:
        :func:`find_best_qubit_layouts` for automatic layout selection.
        :func:`prepare_lg_jobs` for job preparation.
    """

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMFakeBackend = FakeSirius(save_calibration=True)
    if len(qubits_lists) == 0:
        print(f"{datetime.now()}: Selecting best qubits list...")
        qubits_lists = find_best_qubit_layouts(backend)
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_lg_jobs(qubits_lists, backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"{NOW}_iqm_lg_noisy_{backend.name}_results")


def device_pipeline(qubits_lists: list[list[int] | tuple[int, ...]]) -> None:
    """
    Execute a pipeline on a real quantum device using the specified qubit layouts.

    This function prepares the jobs with the specified qubit layouts, runs them on a real quantum backend,
    and saves the results. If no layouts are provided, the function first identifies the best layouts
    based on the cost evaluator before proceeding with job execution.

    Args:
        qubits_lists:
            A list of qubit layouts, where each layout is a list or tuple of integers representing qubit indices.
            If empty, the best layouts are automatically determined using :func:`find_best_qubit_layouts`.

    See Also:
        :func:`find_best_qubit_layouts` for automatic layout selection.
        :func:`prepare_lg_jobs` for job preparation.
    """

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMBackend = get_backend()
    save_calibration()
    if len(qubits_lists) == 0:
        print(f"{datetime.now()}: Selecting best qubits list...")
        qubits_lists = find_best_qubit_layouts(backend)
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_lg_jobs(qubits_lists, backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"{NOW}_iqm_lg_real_{backend.name}_results")
