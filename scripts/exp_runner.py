"""
TODO(TR): Docstring
"""

import ast
import json
import time
from datetime import datetime

import pandas as pd
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMBackendBase, IQMFakeBackend
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit_aer import AerSimulator

from src.jobs import LGACZ2, Job
from src.selector import IQMStarCostEvaluator
from src.simulator import FakeSirius
from src.utils import star_device_transpile

# TODO(TR): Refactor those settings.
# N_JOBS_PER_LAYOUT: int = 10
# N_REPETITIONS: int = 10
# N_SHOTS: int = int(10e4)
N_JOBS_PER_LAYOUT: int = 1
N_REPETITIONS = 1
N_SHOTS: int = int(10e3)
WAIT_TIME: int = 10  # TODO(TR): Adjust or remove.
RESULTS_FOLDER_NAME: str = "./data"
RESULTS_FILE_NAME: str = "job_list_lga_sim2zz.csv"


Backend = AerSimulator | IQMFakeBackend


def find_best_qubit_layouts(backend: IQMFakeBackend, n_layouts: int = 10) -> list[tuple[int, ...]]:
    """TODO(TR): Docstring"""

    # Create a job for evaluator
    job: LGACZ2 = LGACZ2()
    job.n_repetitions = N_REPETITIONS
    job.add_test_circuits([[0, 1, 2]], 0.1)

    circuit: QuantumCircuit = job.circuits[0]

    evaluator: IQMStarCostEvaluator = IQMStarCostEvaluator(backend, circuit)

    best_layouts: list[tuple[tuple[int, ...], float]] = evaluator.get_top_layouts(n_layouts)

    save_layouts_info(best_layouts)

    return [layout for layout, cost in best_layouts]


def save_layouts_info(layouts: list[tuple[tuple[int, ...], float]]) -> None:
    """
    TODO(TR): Docstrings
    """
    layouts_info_dict: dict[str, float] = {str(layout): cost for layout, cost in layouts}

    # Save dict to a file
    with open(f"{RESULTS_FOLDER_NAME}/{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_layouts_info.json", "w") as f:
        json.dump(layouts_info_dict, f, indent=4)


def get_layouts_from_layouts_info(info_file_path: str) -> list[tuple[int, ...]]:
    """TODO(TR): Docstring"""
    try:
        with open(info_file_path, "r") as f:
            layouts: dict[str, float] = json.load(f)

        return [ast.literal_eval(key) for key in layouts.keys()]

    except Exception as e:
        print(e)
        print("Returning empty list to trigger automatic best layers search.")
        return []


def prepare_lg_jobs(qubits_lists: list[list[int] | tuple[int, ...]], backend: Backend) -> list[Job]:
    """TODO(TR): Docstring"""
    jobs: list[Job] = []
    for qubits_list in qubits_lists:
        for _ in range(N_JOBS_PER_LAYOUT):
            job: LGACZ2 = LGACZ2()
            job.n_repetitions = N_REPETITIONS
            job.add_test_circuits([[0, 1, 2]], 0.1)  # Qubits will be adjusted during transpilation.
            jobs.append(job)

        if not issubclass(type(backend), IQMBackendBase):
            continue  # Skip noiseless sim.

        for i in range(len(jobs[-1].circuits)):
            jobs[-1].circuits[i] = star_device_transpile(jobs[-1].circuits[i], backend, qubits_list)

    return jobs


def run_jobs(jobs: list[Job], backend: Backend) -> None:
    """TODO(TR): Docstring"""
    job_list_path: str = f"{RESULTS_FOLDER_NAME}/{RESULTS_FILE_NAME}"
    job_list_table: pd.DataFrame = pd.DataFrame()

    for job in jobs:
        try:
            job.queued_job = backend.run(job.circuits, shots=N_SHOTS)

            print(f"{datetime.now()}: job queued")
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
    """TODO(TR): Docstring"""

    ndone: bool = True

    while ndone:
        ndone = False
        time.sleep(WAIT_TIME)

        for i in range(len(jobs)):
            if jobs[i].update_status():
                print(i, jobs[i].last_status)
                if jobs[i].last_status == "DONE" and not jobs[i].if_saved:
                    filename = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
                    jobs[i].save_to_file(filename, f"{RESULTS_FOLDER_NAME}/{zip_file_name}")
                    print(i, jobs[i].last_status)
                elif jobs[i].last_status in ["ERROR", "CANCELLED"]:
                    print(i, jobs[i].last_status)
                    print(jobs[i].queued_job.error_message())
                    print(jobs[i].queued_job.metrics()["usage"]["quantum_seconds"])

        for job in jobs:
            if job.last_status not in ["ERROR", "CANCELLED", "DONE"]:
                ndone = True


def noiseless_pipeline() -> None:
    """TODO(TR): Docstring"""

    print(f"{datetime.now()}: Preparing backend...")
    backend: Backend = AerSimulator()
    print(f"{datetime.now()}: Preparing jobs...")
    # For noiseless simulations we only need one set of qubits.
    jobs: list[Job] = prepare_lg_jobs(qubits_lists=[[1, 0, 2]], backend=backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name="iqm_lg_noiseless_results")


def noisy_pipeline(qubits_lists: list[list[int] | tuple[int, ...]]) -> None:
    """TODO(TR): Docstring"""

    print(f"{datetime.now()}: Preparing backend...")
    backend: IQMFakeBackend = FakeSirius(save_calibration=True)
    print(f"{datetime.now()}: Selecting best qubits list...")
    if len(qubits_lists) == 0:
        qubits_lists = find_best_qubit_layouts(backend)
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_lg_jobs(qubits_lists, backend)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"iqm_lg_noisy_{backend.name}_results")


def main():
    print("Start")
    # noiseless_pipeline()
    qubits_lists: list[list[int] | tuple[int, ...]] = get_layouts_from_layouts_info(
        "data/2026-07-27_031107_layouts_info.json"
    )
    noisy_pipeline(qubits_lists)
    print("Done")


if __name__ == "__main__":
    main()
