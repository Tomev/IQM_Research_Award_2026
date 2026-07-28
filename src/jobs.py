"""
This script stores our Job classes.
"""

import os
import random
from abc import abstractmethod
from zipfile import ZipFile

import pandas as pd
from numpy import pi
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.primitives import PrimitiveResult


class Job:
    # TODO(TR): Make it a part of TestJob for the sake of this
    # TODO TR: Specify the types, just as in circuits.
    parameters_list = []
    circuits: list[QuantumCircuit] = []
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
        self.result_counts = None

    def update_status(self):
        """TODO(TR): Docsting"""
        status_before_update = self.last_status
        try:
            self.last_status = self.queued_job.status().name
        except Exception as e:
            print(e)
            self.last_status = self.queued_job.status()

        if_changed = True
        if self.last_status == status_before_update:
            if_changed = False

        return if_changed

    # Zapis danych do pliku
    def save_to_file(self, csv_path, zip_filename):
        """TODO(TR): Docstring"""
        raise NotImplementedError

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


class LGA(TestJob):
    """

    .. todo::
        - Remove ecr-based implementation of LGA
        - Add prx-based implementation of
            - sx
            - rz
            - all the other remaining gates

    .. note::
        IQM PRX gate is qiskit RGate.
    """

    def __init__(self) -> None:
        super().__init__()
        self.ep: float = 0
        self.indices_list: list[int] = []
        self.n_repetitions: int = 1
        self.qubits_list = []
        self.qubits_dir = []

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.ecr(i, j)
        c.rz(eps, j)
        c.ecr(i, j)

        # Y_-
        c.rz(pi / 2, j)
        c.sx(j)
        # We can skip the RZ rotation before the measurememt

    def add_test_circuits(self, qubits_list: list[int], epp) -> None:
        """TODO(TR): Refactor according to the intention."""
        self.qubits_list = qubits_list
        self._get_angles_lists()
        self.ep = epp

        self.circuits.clear()

        for s in range(8 * self.n_repetitions):
            cr = []
            for i in range(len(qubits_list)):
                cr.append(ClassicalRegister(3, "cr" + str(i)))
            qreg = QuantumRegister(3)

            # self.circuits.append(QuantumCircuit(2, len(qubits_list)))  # TR: For tests
            #
            self.circuits.append(QuantumCircuit(qreg, *cr))
            for i in range(len(qubits_list)):
                q = qubits_list[i]

                par = self.indices_list[i][s]

                # Zdaje się, że a, b, c to flagi sterujące eksperymentem.
                a = par % 2  # Liczenie kąta pomiaru na qubicie a
                b = (par // 2) % 2  # Liczenie kąta pomiaru na qubicie b
                # Kolejność pomiarów słabych
                c = par // 4

                # print(f"a={a}, b={b}, c={c}")

                # Wartości kątów w zależności od flagi. (-epp lub epp)
                alpha = (2 * a - 1) * epp  # Kąt pomiaru na qubicie a
                beta = (2 * b - 1) * epp  # Kąt pomiaru na qubicie b

                # Y_+ |0> = 1/sqrt(2) (|0> + |1>) state
                self.circuits[-1].sx(q[0])
                self.circuits[-1].rz(pi / 4, q[0])
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
                self.circuits[-1].rz(pi / 4, q[0])
                self.circuits[-1].sx(q[0])
                self.circuits[-1].measure([q[0], q[1], q[2]], cr[i])

    def _get_angles_lists(self):
        for _ in self.qubits_list:
            self.va = []
            for _ in range(self.n_repetitions):
                for i in range(8):
                    self.va.append(i)
            random.shuffle(self.va)
            self.indices_list.append(self.va)

    def save_to_file(self, csv_path, zip_filename):
        """TODO(TR): Docstring"""
        if not self.result_counts:
            self.result_counts = self.queued_job.result().get_counts()

        pandas_table = pd.DataFrame.from_dict(self.result_counts).fillna(0)
        measurement_angle_indices: list[int] = []
        qubit_lists_indices: list[int] = []

        for s in range(8 * self.n_repetitions):
            for qubit_list_index in range(len(self.qubits_list)):
                iva = self.indices_list[qubit_list_index][s]
                measurement_angle_indices.append(iva)
                qubit_lists_indices.append(qubit_list_index)
        pandas_table["i"] = measurement_angle_indices
        pandas_table["qubits_set_index"] = qubit_lists_indices

        # Saving to file
        pandas_table.to_csv(csv_path)
        csv_filename = csv_path.split("/")[-1]

        with ZipFile(zip_filename + ".zip", "a") as zip_file:
            zip_file.write(csv_path, arcname="results/" + csv_filename)
        self.if_saved = True

        try:
            os.remove(csv_path)
        except Exception as alert:
            print(alert)

        self.result_counts = None


class LGACZ(LGA):
    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.sx(j)
        c.rz(eps + pi, j)
        c.sx(j)
        c.cz(i, j)
        c.rz(-pi / 2, j)
        c.sx(j)


class LGACZ2(LGA):
    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.cz(i, j)
        c.sx(j)
        c.rz(eps + pi, j)
        c.sx(j)
        c.rz(pi, j)
        c.cz(i, j)

        # Y_-
        c.rz(pi / 2, j)
        c.sx(j)


class LGACZX(LGA):
    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.rx(eps, j)
        c.cz(i, j)
        c.rz(pi, j)
        c.sx(j)


class LGACZ2X(LGA):
    def __init__(self):
        super().__init__()

    @staticmethod
    def we(c: QuantumCircuit, i, j, eps):
        c.cz(i, j)
        c.rx(eps, j)
        c.cz(i, j)
        c.rz(pi, j)
        c.sx(j)
