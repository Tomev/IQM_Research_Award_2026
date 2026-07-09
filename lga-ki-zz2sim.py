import sys
import time
import matplotlib.pyplot as plt
import datetime

import pandas as pd
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.fake_provider import FakeBrisbane,FakeProviderForBackendV2,FakeSherbrooke
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from joblgan import LGACZ2
from qiskit.primitives import StatevectorSampler
 

from settingscloud import *



def run_scripts():
    jobs = []
    job_list_table = pd.DataFrame()

    # Job preparation
    #ky
    #qubits_list=[[6,5,7]]
    qubits_list=[[1, 0, 2]]
    for _ in range(N_JOBS):
        job = LGACZ2()
        job.n_repetitions = N_REPETITIONS
        job.add_test_circuits(qubits_list,0.1)
        jobs.append(job)
    
    i = 0
    job_list_path = f"{RESULTS_FOLDER_NAME}/job_list_lga_sim2zz.csv"
    while i < N_JOBS:
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print("Starting service")
        tok,crn,nm=tcset[0]
        service = QiskitRuntimeService(channel="ibm_cloud",instance=crn,token=tok)    
        print(i,nm)
        t = time.localtime()
        #backend = service.backend('ibm_kingston', use_fractional_gates=True)
        aer_sim = AerSimulator()
        backend=aer_sim
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print("pass manager",current_time)
        pm = generate_preset_pass_manager(backend=backend,optimization_level=0)
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print("pass manager done",current_time)
        isa_cir=pm.run(jobs[i].circuits)
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print("ISA",current_time)
        
        sampler = Sampler(backend)
        #sampler = StatevectorSampler()
        #print(backend)
        try:
            jobs[i].queued_job = sampler.run(isa_cir, shots=N_SHOTS)
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            print("job queued",current_time)
            job_data = {
                "job_id": jobs[i].queued_job.job_id(),
                "pars": jobs[i].indices_list,
                "token_id": nm
            }
            job_list_table = pd.concat(
                [job_list_table, pd.DataFrame([job_data])], ignore_index=True
            )
            job_list_table.to_csv(job_list_path)
            t = time.localtime()
            i += 1
        except Exception as alert:
            print(alert)
            time.sleep(WAIT_TIME)
    ndone = True

    while ndone:
        ndone = False
        time.sleep(WAIT_TIME)
        for i in range(N_JOBS):
            if jobs[i].update_status():
                print(i,jobs[i].last_status)
                if jobs[i].last_status == "DONE" and not jobs[i].if_saved:
                    filename = (
                        f"{RESULTS_FOLDER_NAME}/results_tests_{str(i)}.csv"
                    )
                    jobs[i].save_to_file(filename, ZIP_FILE_NAME)
                    print(i,  jobs[i].last_status)
                elif jobs[i].last_status in ["ERROR", "CANCELLED"]:
                    print(i,  jobs[i].last_status)
                    print(jobs[i].queued_job.error_message())
                    print(jobs[i].queued_job.metrics()["usage"]["quantum_seconds"])
        for i in range(N_JOBS):
            if jobs[i].last_status not in ["ERROR", "CANCELLED", "DONE"]:
                ndone = True
                #print(jobs[i].last_status)

    experiments_cleen_up(job_list_path)

def main():
    print("Start")
    run_scripts()
    print("Done")


if __name__ == "__main__":
    main()
