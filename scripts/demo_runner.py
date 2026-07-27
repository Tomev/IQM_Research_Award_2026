""" """

import time
from datetime import datetime

import pandas as pd
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from src.jobs import LGACZ2, Job
from src.simulator import FakeSirius

# TODO(TR): Refactor those settings.
N_JOBS: int = 4
N_REPETITIONS: int = 4
N_SHOTS: int = 1024
WAIT_TIME: int = 10  # TODO(TR): Adjust or remove.
RESULTS_FOLDER_NAME: str = "./data"
RESULTS_FILE_NAME: str = "job_list_lga_sim2zz.csv"
ZIP_FILE_NAME: str = "iqm_lg_results"  # No extension.


def run_scripts():
    """TODO(TR): Docstring this."""
    jobs: list[Job] = []
    job_list_table = pd.DataFrame()

    # Job preparation
    qubits_list: list[list[int]] = [[1, 0, 2]]
    for _ in range(N_JOBS):
        job = LGACZ2()
        job.n_repetitions = N_REPETITIONS
        job.add_test_circuits(qubits_list, 0.1)
        jobs.append(job)

    i: int = 0
    job_list_path = f"{RESULTS_FOLDER_NAME}/{RESULTS_FILE_NAME}"

    # backend = IQMFakeDeneb()
    print(f"{datetime.now()}: Preparing FakeSirius")
    backend = FakeSirius()

    while i < N_JOBS:
        print(f"{datetime.now()}: Starting service")

        print(f"{datetime.now()}: pass manager")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)

        print(f"{datetime.now()}: pass manager done")
        isa_cir = pm.run(jobs[i].circuits)

        print(f"{datetime.now()}: ISA")

        try:
            jobs[i].queued_job = backend.run(isa_cir, shots=N_SHOTS)

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

    # TR: Main experimental loop
    ndone: bool = True

    while ndone:
        ndone = False
        time.sleep(WAIT_TIME)
        for i in range(N_JOBS):
            if jobs[i].update_status():
                print(i, jobs[i].last_status)
                if jobs[i].last_status == "DONE" and not jobs[i].if_saved:
                    filename = f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
                    jobs[i].save_to_file(filename, f"{RESULTS_FOLDER_NAME}/{ZIP_FILE_NAME}")
                    print(i, jobs[i].last_status)
                elif jobs[i].last_status in ["ERROR", "CANCELLED"]:
                    print(i, jobs[i].last_status)
                    print(jobs[i].queued_job.error_message())
                    print(jobs[i].queued_job.metrics()["usage"]["quantum_seconds"])
        for i in range(N_JOBS):
            if jobs[i].last_status not in ["ERROR", "CANCELLED", "DONE"]:
                ndone = True


def main():
    print("Start")
    run_scripts()
    print("Done")


if __name__ == "__main__":
    main()
