"""A module with qubit selector training

.. note::
    IQM Qubit Selector is programmed to work with the crystal topology devices. It
"""

import os
from itertools import combinations

from iqm.qiskit_iqm import IQMBackend, IQMProvider
from iqm.qubit_selector.qubit_selector import CostEvaluator
from tqdm import tqdm

from src.jobs import LGACZ2


def find_lgi_triplets(backend: IQMBackend) -> list[dict[str, int]]:
    """
    Given the IBM backend, find the qubit triplets for the Laggett-Garg test experiment.
    We require that qubits X, A, B are connected in the following way:

    X -> A

    and

    X -> B,

    where the arrow denotes the direction of the entangling gate.

    :params:
        backend:     IBM backend.

    :return:
        A list of LGI-eligible qubit triplets.
    """
    lgi_triplets: list[dict[str, int]] = []

    coupling_map = backend.coupling_map

    def format_connection(con: list[list[int]]):
        return {"x": con[0][0], "a": con[1][0], "b": con[1][1]}

    for x in tqdm(range(backend.num_qubits)):
        # Find all qubits that x can control.
        connections = find_qubit_connections(backend, x)

        if len(connections) < 2:
            continue

        if len(connections) > 2:
            # Prepare 2-length permutations of the connections.
            connections = list(combinations(connections, 2))
        if len(connections) == 2:
            connections = [connections]  # Hax for more general processing.

        for con in connections:
            lgi_triplets.append(format_connection([[x], con]))

    return lgi_triplets


def find_qubit_connections(backend: IQMBackend, qubit: int) -> list[int]:
    """
    Find all qubits that are connected to the given qubit.

    :params:
        backend:     IBM backend.
        qubit:       The qubit to check connections for.

    :return:
        A list of connections in the backend that qubit controls.
    """
    coupling_map = backend.coupling_map

    return [con[1] for con in coupling_map if con[0] == qubit]


def main() -> None:
    """
    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
        # quantum_computer="garnet",
    )
    backend: IQMBackend = provider.get_backend()

    triplets: list[dict[str, int]] = find_lgi_triplets(backend)
    for triplet in triplets:
        print(triplet)
    print(f"# triplets: {len(triplets)}")


    fidelities = CalibrationDataManager().get_calibration_fidelities(backend)

    for k, v in fidelities.items():
        print(f"\n\n{k}: {v}")

    # print(fidelities)
    """

    iqm_qubit_selection()


def iqm_qubit_selection() -> None:
    """TODO(TR): Docstring

    .. note::
        Dropped for now, due to the lack of IQM Qubit Selector support for star topology devices.
    """

    provider: IQMProvider = IQMProvider(
        os.environ["IQM_PROVIDER"],
        quantum_computer=os.environ["IQM_COMPUTER"],
        # quantum_computer="garnet",
    )
    backend: IQMBackend = provider.get_backend()

    n_best_layouts: int = 3

    qubits_list: list[list[int]] = [[1, 0, 2]]
    job: LGACZ2 = LGACZ2()
    job.n_repetitions = 1
    job.add_test_circuits(qubits_list, 0.1)

    circuit = job.circuits[0]  # Do not transpile it, because it causes problems with "move" gate later!

    layouts, cost = CostEvaluator(backend=backend, quantum_circuit=circuit).get_top_layouts(num_layouts=n_best_layouts)
    print(f"Top {n_best_layouts} qiskit layouts and their costs:")
    for layout, c in zip(layouts[:n_best_layouts], cost[:n_best_layouts]):
        print(f"Layout: {layout}, Cost: {c * 100:.2f}%")


if __name__ == "__main__":
    print("Start")
    main()
    print("Done")
