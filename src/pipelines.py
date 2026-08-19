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
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from exa.common.data.setting_node import SettingNode
from iqm.pulla.pulla import Pulla, PullaStash
from iqm.pulla.utils_qiskit import qiskit_to_pulla, sweep_job_to_qiskit
from iqm.qiskit_iqm import IQMProvider
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMBackendBase, IQMFakeBackend
from iqm.qiskit_iqm.iqm_provider import IQMBackend
from iqm.qubit_selector.qubit_selector import CostEvaluator
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit_aer import AerSimulator

from src.jobs import LGACZ2, Job
from src.selector import IQMStarCostEvaluator
from src.simulator import FakeFromBackend
from src.utils import get_backend, get_configuration_dicts, star_device_transpile

# TODO(TR): Refactor those settings.
# There are 8 angles per layout in the job. This means the number of circuits in a single job is equal to
#   N_CIRCUITS = 8 x N_REPETITIONS
#
# Prefered setup is N_REPETITONS = 10, meaning that we can only handle 1 qubit layout per job. That is because maximal
# number of circuits per job is 100 (on IQM Sirius).
#

# SYSTEM_NAME: str = "sirius"
SYSTEM_NAME: str = "emerald"
N_JOBS_PER_LAYOUT: int = 3
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


@dataclass
class PullaSettings:
    cz_amplitude_multiplier: float | None = None
    measure_amplitude_multiplier: float | None = None
    prx_amplitude_multiplier: float | None = None


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
    best_layouts: list[tuple[tuple[int, ...], float]] = []

    if backend.name == "sirius":
        evaluator: IQMStarCostEvaluator = IQMStarCostEvaluator(backend, circuit)
        best_layouts = evaluator.get_top_layouts(n_layouts)
    else:
        layouts, costs = CostEvaluator(backend=get_backend(backend.name), quantum_circuit=circuit).get_top_layouts(
            num_layouts=n_layouts
        )
        for i in range(len(layouts)):
            print(f"{layouts[i]}: {costs[i]}")
            best_layouts.append((layouts[i], costs[i]))

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
    print("Downloading configuration dicts...")
    calibration_dict: dict[str, Any]
    quality_dict: dict[str, Any]
    calibration_dict, quality_dict = get_configuration_dicts(SYSTEM_NAME)

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMFakeBackend = FakeFromBackend(SYSTEM_NAME, calibration_dict, quality_dict)
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
    print("Downloading configuration dicts...")
    get_configuration_dicts(SYSTEM_NAME)  # Saves the system configuration during run.

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMBackend = get_backend()

    if len(qubits_lists) == 0:
        print(f"{datetime.now()}: Selecting best qubits list...")
        qubits_lists = find_best_qubit_layouts(backend)
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_lg_jobs(qubits_lists, backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"{NOW}_iqm_lg_real_{backend.name}_results")


def pulla_pipeline(qubits_lists: list[list[int] | tuple[int, ...]], settings: PullaSettings) -> None:
    """
    TODO(TR): Update!

    Execute a pipeline using the Pulla framework with damped CZ gate amplitudes on a real quantum device.

    Args:
        qubits_lists:
            A list of qubit layouts, where each layout is a list or tuple of integers representing qubit indices.
            If empty, the best layouts are automatically determined using :func:`find_best_qubit_layouts`.
        cz_amplitude_multiplier:
            A multiplier factor applied to the CZ gate amplitudes in the calibration settings.
            This allows for tuning the gate strengths for specific experimental purposes.

    Notes:
        This function prepares the jobs with the specified qubit layouts, runs them on a real quantum backend
        using the Pulla framework, and saves the results. The CZ gate amplitudes in the calibration settings
        are adjusted by the given multiplier before execution. If no layouts are provided, the function
        first identifies the best layouts based on the cost evaluator before proceeding with job execution.

    See Also:
        :func:`find_best_qubit_layouts` for automatic layout selection.
        :func:`execute_with_pulla` for the core execution logic with Pulla.
    """
    print("Downloading configuration dicts...")
    get_configuration_dicts(SYSTEM_NAME)  # Saves the system configuration during run.

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMBackend = get_backend()

    if len(qubits_lists) == 0:
        print(f"{datetime.now()}: Selecting best qubits list...")
        qubits_lists = find_best_qubit_layouts(backend)
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_lg_jobs(qubits_lists, backend)
    print(f"{datetime.now()}: Execute jobs with pulla...")
    execute_with_pulla(jobs, backend, settings)


def execute_with_pulla(qiskit_jobs: list[Job], backend: IQMBackend, compilation_settings: PullaSettings) -> None:
    """
    TODO(TR): Update!

    Execute a quantum job using the Pulla framework with modified CZ gate amplitudes.

    Args:
        qiskit_jobs:
            A list of :class:`Job` instances containing quantum circuits to be executed.
        backend:
            The quantum backend to use for execution, which must be an :class:`IQMBackend`.
        cz_amplitude_multiplier:
            A multiplier factor applied to the CZ gate amplitudes in the calibration settings.
            This allows for tuning the gate strengths for specific experimental purposes.

    Notes:
        This function is responsible for converting Qiskit circuits to Pulla format, adjusting the
        calibration settings with the specified CZ amplitude multiplier, compiling the job definition,
        submitting the job to the backend, and saving the results in JSON format.

    See Also:
        :func:`pulla_pipeline` for the high-level function that orchestrates the entire Pulla workflow.
    """
    job_list_path: str = f"{RESULTS_FOLDER_NAME}/{NOW}_{RESULTS_FILE_NAME}"
    job_list_table: pd.DataFrame = pd.DataFrame()

    print(f"{datetime.now()}: Getting pulla...")
    # Define the standard compiler that loads the default calibration set as its initial operating point.
    pulla: Pulla = Pulla(os.environ["IQM_PROVIDER"], quantum_computer=os.environ["IQM_COMPUTER"])

    for i, job in enumerate(qiskit_jobs):
        print(f"{datetime.now()}: Preparing job {i + 1} pulla circuits and compiler...")
        pulla_circuits, compiler = qiskit_to_pulla(pulla, backend, job.circuits)
        print(f"{datetime.now()}: Getting pulla compiler settings...")
        settings: SettingNode = compiler.get_settings(circuits=pulla_circuits)
        print(f"{datetime.now()}: Adjusting pulla settings...")
        settings.set_shots(N_SHOTS)
        if compilation_settings.cz_amplitude_multiplier:
            modify_cz_amplitudes(pulla, settings, compilation_settings.cz_amplitude_multiplier)
        if compilation_settings.measure_amplitude_multiplier:
            modify_measure_amplitudes(pulla, settings, compilation_settings.measure_amplitude_multiplier)
        if compilation_settings.prx_amplitude_multiplier:
            modify_prx_amplitudes(pulla, settings, compilation_settings.measure_amplitude_multiplier)

        print(f"{datetime.now()}: Compiling pulla job definition...")
        job_definition, context = compiler.compile(pulla_circuits, settings=settings)
        print(f"{datetime.now()}: Running job {i + 1} (of {len(qiskit_jobs)})...")
        # Save the job data first, so that the order of steering bits is not lost!
        pulla_job = pulla.submit_playlist(job_definition, context=context)
        job.queued_job = pulla_job
        job_data: dict = {
            "job_id": job.queued_job.job_id,
            "pars": job.indices_list,
            "cz_amp_mod": compilation_settings.cz_amplitude_multiplier,
            "prx_amp_mod": compilation_settings.prx_amplitude_multiplier,
            "measure_amp_mod": compilation_settings.measure_amplitude_multiplier,
        }
        job_list_table = pd.concat([job_list_table, pd.DataFrame([job_data])], ignore_index=True)
        job_list_table.to_csv(job_list_path)
        print(f"{datetime.now()}: Waiting for job {i + 1} to finish...")
        pulla_job.wait_for_completion()
        print(f"{datetime.now()}: Job finished.")
        results_file_path: str = f"{RESULTS_FOLDER_NAME}/{NOW}_pulla_{i}.json"
        print(f"{datetime.now()}: Saving counts to {results_file_path}...")
        qiskit_result = sweep_job_to_qiskit(pulla_job, shots=N_SHOTS)
        job.result_counts = qiskit_result.get_counts()
        print(job.result_counts)  # Just in case

        with open(results_file_path, "w", encoding="utf-8") as f:
            json.dump(job.result_counts, f, indent=4)

        csv_path: str = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
        zip_file_name: str = f"{NOW}_iqm_lg_pulla_{backend.name}_results"

        job.save_to_file(csv_path, f"{RESULTS_FOLDER_NAME}/{zip_file_name}")


def modify_cz_amplitudes(pulla: Pulla, settings: SettingNode, cz_amplitude_multiplier: float) -> None:
    """
    Modify the CZ gate amplitudes in the Pulla calibration settings based on the given multiplier.

    Args:
        pulla:
            The Pulla instance used for calibration and job execution.
        settings:
            The :class:`SettingNode` containing the current calibration settings.
        cz_amplitude_multiplier:
            A multiplier factor applied to the CZ gate amplitudes in the calibration settings. This allows
            for tuning the gate strengths for specific experimental purposes.

    Notes:
        This function retrieves the current calibration stash from the Pulla instance, computes the modified CZ
        amplitudes by applying the multiplier, and updates the :class:`SettingNode` with the new values.
    """
    modified_amplitudes: dict[str, float] = compute_modified_cz_amplitude(pulla, cz_amplitude_multiplier)

    for key, v in modified_amplitudes.items():
        settings[key] = v


def compute_modified_cz_amplitude(pulla: Pulla, amplitude_multiplier: float = 0.8) -> dict[str, float]:
    """
    Compute the modified CZ gate amplitudes based on a given multiplier.

    Args:
        pulla:
            The :class:`Pulla` instance containing the calibration stash.
        amplitude_multiplier:
            A multiplier factor applied to the CZ gate amplitudes in the calibration settings.
            This allows for tuning the gate strengths for specific experimental purposes.

    Returns:
        A dictionary containing the modified CZ gate amplitudes, where keys are parameter names
        and values are the new amplitude values.

    Notes:
        This function iterates over the calibration stash, identifies parameters containing
        "amplitude" and "cz" in their names, and multiplies their values by the provided
        amplitude multiplier.
    """

    calibration_stash: PullaStash = pulla.get_calibration_stash()
    calibration_override: dict[str, float] = {}

    for k, v in calibration_stash.observations.items():
        if "amplitude" in k and "cz" in k:
            calibration_override[k] = v.value * amplitude_multiplier
            # print(f"{k}: {v.value} vs {calibration_override[k]}")

    return calibration_override


def modify_measure_amplitudes(pulla: Pulla, settings: SettingNode, cz_amplitude_multiplier: float) -> None:
    """TODO(TR): ..."""
    modified_amplitudes: dict[str, float] = compute_modified_cz_amplitude(pulla, cz_amplitude_multiplier)

    for key, v in modified_amplitudes.items():
        settings[key] = v


def compute_modified_measure_amplitude(pulla: Pulla, amplitude_multiplier: float) -> dict[str, float]:
    """TODO(TR): ..."""

    calibration_stash: PullaStash = pulla.get_calibration_stash()
    calibration_override: dict[str, float] = {}

    for k, v in calibration_stash.observations.items():
        if "amplitude" in k and "measure" in k:
            calibration_override[k] = v.value * amplitude_multiplier
            # print(f"{k}: {v.value} vs {calibration_override[k]}")

    return calibration_override


def modify_prx_amplitudes(pulla: Pulla, settings: SettingNode, cz_amplitude_multiplier: float) -> None:
    """
    TODO(TR): ...
    """
    modified_amplitudes: dict[str, float] = compute_modified_prx_amplitude(pulla, cz_amplitude_multiplier)

    for key, v in modified_amplitudes.items():
        settings[key] = v


def compute_modified_prx_amplitude(pulla: Pulla, amplitude_multiplier: float) -> dict[str, float]:
    """TODO(TR): ..."""

    calibration_stash: PullaStash = pulla.get_calibration_stash()
    calibration_override: dict[str, float] = {}

    for k, v in calibration_stash.observations.items():
        if "amplitude_i" in k and "prx" in k:
            calibration_override[k] = v.value * amplitude_multiplier
            # print(f"{k}: {v.value} vs {calibration_override[k]}")

    return calibration_override
