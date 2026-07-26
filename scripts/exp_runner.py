""" """

import time
from datetime import datetime

import pandas as pd
from iqm.qiskit_iqm.fake_backends.iqm_fake_backend import IQMFakeBackend
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

from src.jobs import LGACZ2, Job
from src.simulator import FakeSirius

# TODO(TR): Refactor those settings.
# N_JOBS: int = 10
# N_REPETITIONS: int = 10
# N_SHOTS: int = int(10e4)
N_JOBS: int = 1
N_REPETITIONS = 1
N_SHOTS: int = int(10e3)
WAIT_TIME: int = 10  # TODO(TR): Adjust or remove.
RESULTS_FOLDER_NAME: str = "./data"
RESULTS_FILE_NAME: str = "job_list_lga_sim2zz.csv"
ZIP_FILE_NAME: str = "iqm_lg_results"  # No extension.


Backend = AerSimulator | IQMFakeBackend


def prepare_jobs(qubits_lists: list[list[int] | tuple[int, ...]]) -> list[Job]:
    """TODO(TR): Docstring"""
    jobs: list[Job] = []
    for qubits_list in qubits_lists:
        for _ in range(N_JOBS):
            job: LGACZ2 = LGACZ2()
            job.n_repetitions = N_REPETITIONS
            job.add_test_circuits([qubits_list], 0.1)
            jobs.append(job)
    return jobs


def run_jobs(jobs: list[Job], backend: Backend) -> None:
    """TODO(TR): Docstring"""
    i: int = 0
    job_list_path = f"{RESULTS_FOLDER_NAME}/{RESULTS_FILE_NAME}"
    job_list_table: pd.DataFrame = pd.DataFrame()

    for i in range(N_JOBS):
        try:
            jobs[i].queued_job = backend.run(jobs[i].circuits, shots=N_SHOTS)

            print(f"{datetime.now()}: job queued")
            job_data = {
                "job_id": jobs[i].queued_job.job_id(),
                "pars": jobs[i].indices_list,
            }
            job_list_table = pd.concat([job_list_table, pd.DataFrame([job_data])], ignore_index=True)
            job_list_table.to_csv(job_list_path)
            i += 1
        except Exception as alert:
            print(alert)
            time.sleep(WAIT_TIME)


def wait_and_save_results(jobs: list[Job], zip_file_name: str) -> None:
    """TODO(TR): Docstring"""

    ndone: bool = True

    while ndone:
        ndone = False
        time.sleep(WAIT_TIME)

        for i in range(N_JOBS):
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
        for i in range(N_JOBS):
            if jobs[i].last_status not in ["ERROR", "CANCELLED", "DONE"]:
                ndone = True


def noiseless_pipeline() -> None:
    """TODO(TR): Docstring"""

    print(f"{datetime.now()}: Preparing backend...")
    backend: Backend = AerSimulator()
    print(f"{datetime.now()}: Preparing jobs...")
    # For noiseless simulations we only need one set of qubits.
    jobs: list[Job] = prepare_jobs(qubits_lists=[[1, 0, 2]])
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name="iqm_lg_noiseless_results")


def noisy_pipeline(find_best_qubits: bool = False) -> None:
    """TODO(TR): Docstring"""

    print(f"{datetime.now()}: Preparing backend...")
    backend: Backend = FakeSirius()
    print(f"{datetime.now()}: Selecting best qubits list...")
    # TODO(TR): Add best qubits selection
    qubits_lists: list[list[int] | tuple[int, ...]] = [[1, 0, 2], [3, 4, 5]]
    print(f"{datetime.now()}: Preparing jobs...")
    jobs: list[Job] = prepare_jobs(qubits_lists)
    print(f"{datetime.now()}: Running jobs...")
    run_jobs(jobs, backend)
    print(f"{datetime.now()}: Waiting and saving results...")
    wait_and_save_results(jobs, zip_file_name=f"iqm_lg_noisy_{backend.name}_results")


def main():
    print("Start")
    # noiseless_pipeline()
    noisy_pipeline()
    print("Done")


if __name__ == "__main__":
    main()
