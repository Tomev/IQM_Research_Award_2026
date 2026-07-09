"""
This script stores our Job classes. 
"""

import os
import random
from abc import abstractmethod
from typing import Dict, List
from zipfile import ZipFile

import numpy as np
import pandas as pd
from numpy import pi
from qiskit import ClassicalRegister, QuantumRegister
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives import PrimitiveResult


class Job:
    # TODO TR: Specify the types, just as in circuits.
    parameters_list = []
    circuits: List[QuantumCircuit] = []
    last_status = None
    queued_job = None
    status = None
    test_circuits_number = None
    if_saved: bool = False

    def __init__(self) -> None:
        self.parameters_list = []
        self.circuits = []
        self.status = None
        self.queued_job = None
        self.last_status = None
        self.test_circuits_number = None
        self.if_saved = False

    def add_sanity_test_circuits(self, test_number: int) -> None:
        """
        Sanity check test circuits.
        """
        self.test_circuits_number = test_number

        circuit_test_0 = QuantumCircuit(1, 1)
        circuit_test_0.measure(0, 0)

        circuit_test_1 = QuantumCircuit(1, 1)
        circuit_test_1.x(0)
        circuit_test_1.measure(0, 0)

        for _ in range(0, test_number):
            self.circuits.append(circuit_test_0)
            self.circuits.append(circuit_test_1)

    def update_status(self):
        status_before_update = self.last_status
        try:
            self.last_status = self.queued_job.status().name
        except:
            self.last_status = self.queued_job.status()

        if_changed = True
        if self.last_status == status_before_update:
            if_changed = False

        return if_changed

    # Zapis danych do pliku
    def save_to_file(self, csv_path, zip_filename):

        results = self.get_counts_from_job_results(self.queued_job)

        results = self.queued_job.result().get_counts()
        tabela = pd.DataFrame.from_dict(results).fillna(0)

        theta = []
        # część testowa
        # for i in range(0, 2 * self.test_circuits_number):
        #   theta.append("TEST")
        # kąty w odpowiedniej kolejności
        # theta.extend(self.parameters_list)
        for n in range(101):
            theta.append(f"Test_Circuit_n_{n}")

        print(tabela)

        # dodanie właściwej kolumny do danych
        tabela["theta"] = theta
        tabela.to_csv(csv_path)

        csv_filename = csv_path.split("/")[-1]
        with ZipFile(zip_filename + ".zip", "a") as plik_zip:
            plik_zip.write(csv_path, arcname="results/" + csv_filename)

        self.if_saved = True

        try:
            os.remove(csv_path)
        except Exception as alert:
            print(alert)

    @staticmethod
    def get_counts_from_job_results(job):
        """
        Get counts from the job.

        Job results, returned by differently executed jobs (eg. by a sampler
        or by a backend) have a different structure. This method is supposed
        to be overwritten in the child classes, to provide a unified way of
        getting counts from the job results.
        """
        # TODO TR:  We might require some try-except block here, expecting
        #           different types of job results.

        results = job.result()
        counts = []

        # Check if type is PrimitiveResult
        if isinstance(results, PrimitiveResult):
            # This is for the case when the job is executed by a sampler.

            # print(f"\n{results}\n")
            # print(f"\n{results[0]}\n")
            # print(f"\n{results[0].data}\n")

            # TODO TR:  This assumes that the register is called "c". That
            #           might not be the case for all the results.

            counts = []

            for result in results:
                counts.append(result.data.c.get_counts())

        else:
            # This is for the case when the job is executed by a backend.
            counts = results.get_counts()

        # print(f"\n{counts}\n")

        return counts




class TestJob(Job):
    """
    An abstract class for Test jobs.
    """

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def add_test_circuits(self, test_number: int) -> None:
        """
        Adds test circuits to the job.
        """
        raise NotImplementedError
    
    def save_to_file(self, csv_path, zip_filename):
        result_counts=[]
        
        job_result = self.queued_job.result()
        for pub_result in job_result:
            for i in range(len(self.qubits_list)):
                result_counts.append(getattr(pub_result.data, "cr"+str(i)).get_counts())
        pandas_table = pd.DataFrame.from_dict(result_counts).fillna(0)

        indices_i=[]
        indices_q=[]

        for s in range(8*self.n_repetitions):
            for q in range(len(self.qubits_list)):
                iva=self.indices_list[q][s]
                indices_i.append(iva)
                indices_q.append(q)
        pandas_table["i"] = indices_i
        pandas_table["q"] = indices_q
        
        # Saving to file
        pandas_table.to_csv(csv_path)
        csv_filename = csv_path.split('/')[-1]
        with ZipFile(zip_filename + '.zip', 'a') as plik_zip:
            plik_zip.write(csv_path, arcname='results/' + csv_filename)
        self.if_saved = True

        try:
            os.remove(csv_path)
        except Exception as alert:
            print(alert)

class LGA(TestJob):

    def __init__(self) -> None:
        super().__init__()
        self.ep = 0
        self.indices_list = []
        self.n_repetitions = 1
        self.qubits_list = []
        self.qubits_dir = []

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        
        c.ecr(i, j)
        c.rz(eps, j)
        c.ecr(i, j)

        # Y_-
        c.rz(np.pi / 2, j)
        c.sx(j)
        # We can skip the RZ rotation before the measurememt
    #@staticmethod
    #def we(c: QuantumCircuit, i, j, eps):
    #    c.sx(j)
    #    c.rz(eps+np.pi/2, j)
    #    c.ecr(i, j)
    #    c.rz(np.pi/2,i)
    #    c.x(i)
        
    def add_test_circuits(self, qubits_list: List[int], epp) -> None:
        self.qubits_list = qubits_list
        self._get_angles_lists()
        self.ep = epp

        self.circuits.clear()

        for s in range(8 * self.n_repetitions):
            # self.circuits.append(QuantumCircuit(127, len(listvert)))
            cr = []
            for i in range(len(qubits_list)):
                cr.append(ClassicalRegister(3, "cr" + str(i)))
            qreg = QuantumRegister(3)
            # self.circuits.append(QuantumCircuit(2, len(qubits_list)))  # TR: For tests
            self.circuits.append(QuantumCircuit(qreg, *cr))
            for i in range(len(qubits_list)):
                q = qubits_list[i]

                # print(self.indices_list)

                par = self.indices_list[i][s]

                # print(par)

                # Zdaje się, że a, b, c to flagi sterujące eksperymentem.
                a = par % 2             # Liczenie kąta pomiaru na qubicie a
                b = (par // 2) % 2      # Liczenie kąta pomiaru na qubicie b
                # Kolejność pomiarów słabych
                c=par//4

                # print(f"a={a}, b={b}, c={c}")

                # Wartości kątów w zależności od flagi. (-epp lub epp)
                alpha = (2 * a - 1) * epp   # Kąt pomiaru na qubicie a
                beta = (2 * b - 1) * epp    # Kąt pomiaru na qubicie b

                aa = np.pi / 4
                bb = -np.pi / 4

                # Y_+ |0> = 1/sqrt(2) (|0> + |1>) state
                self.circuits[-1].sx(q[0])
                self.circuits[-1].rz(np.pi / 4, q[0])
                self.circuits[-1].sx(q[0])

                # TODO TR: Refactor that if.
                if c:
                    self.we(self.circuits[-1], q[0], q[1], alpha)
                    self.we(self.circuits[-1], q[0], q[2], beta)
                else:
                    self.we(self.circuits[-1], q[0], q[2], beta)
                    self.we(self.circuits[-1], q[0], q[1], alpha) 
                self.circuits[-1].z(q[0])
                self.circuits[-1].sx(q[0])
                self.circuits[-1].rz(np.pi / 4, q[0])
                self.circuits[-1].sx(q[0])          
                self.circuits[-1].measure([q[0], q[1], q[2]], cr[i])

    def _get_angles_lists(self):
        for v in self.qubits_list:
            self.va = []
            for n in range(self.n_repetitions):
                for i in range(8):
                    self.va.append(i)
            random.shuffle(self.va)
            self.indices_list.append(self.va)

    def save_to_file(self, csv_path, zip_filename):
        result_counts=[]
        job_result = self.queued_job.result()
        for pub_result in job_result:
            for i in range(len(self.qubits_list)):
                result_counts.append(getattr(pub_result.data, "cr"+str(i)).get_counts())
        pandas_table = pd.DataFrame.from_dict(result_counts).fillna(0)
        indices_i=[]
        indices_q=[]
        #qubits_list=self.qubits_list
        for s in range(8*self.n_repetitions):
            for q in range(len(self.qubits_list)):
                iva=self.indices_list[q][s]
                indices_i.append(iva)
                indices_q.append(q)
        pandas_table["i"] = indices_i
        pandas_table["q"] = indices_q
        
        # Saving to file
        pandas_table.to_csv(csv_path)
        csv_filename = csv_path.split('/')[-1]
        with ZipFile(zip_filename + '.zip', 'a') as plik_zip:
            plik_zip.write(csv_path, arcname='results/' + csv_filename)
        self.if_saved = True

        try:
            os.remove(csv_path)
        except Exception as alert:
            print(alert)
        
class LGASingleGate(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.sx(j)
        c.rz(eps + np.pi / 2, j)
        c.ecr(i, j)
        c.rz(np.pi / 2, i)
        c.x(i)
class LGACZ(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):   
        c.sx(j)
        c.rz(eps + np.pi, j)
        c.sx(j)
        c.cz(i,j)
        c.rz(-np.pi / 2, j)
        c.sx(j)
class LGACZ2(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):   
        c.cz(i, j)
        c.sx(j)
        c.rz(eps+np.pi, j)
        c.sx(j)
        c.rz(np.pi, j)
        c.cz(i, j)

        # Y_-
        c.rz(np.pi / 2, j)
        c.sx(j)
class LGACZX(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):   
        c.rx(eps,j)
        c.cz(i,j)
        c.rz(np.pi, j)
        c.sx(j)
class LGACZ2X(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.cz(i, j)
        c.rx(eps,j)
        c.cz(i,j)
        c.rz(np.pi, j)
        c.sx(j)
class LGAZZ(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):   
        if eps>=0:
            c.rz(-np.pi/2,j)
            c.sx(j) 
            c.rzz(eps,  i, j)
            c.rz(np.pi/2,j)
            c.sx(j)
        else:
            c.rz(np.pi/2,j)
            c.sx(j)
            c.rzz(-eps,  i, j)
            c.rz(-np.pi/2,j)
            c.sx(j)
class LGAZZ0(LGA):

    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):   
        if eps>=0:
            c.rz(-np.pi/2,j)
            c.sx(j) 
            c.rzz(eps,  i, j)
            c.rz(np.pi/2,j)
            c.sx(j)
        else:
            c.rz(-np.pi/2,j)
            c.sx(j) 
            c.rzz(0,  i, j)
            c.rz(np.pi/2,j)
            c.sx(j)
