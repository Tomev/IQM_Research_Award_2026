"""
This script serves as the main entry point for executing quantum computing pipelines. It initializes the process, runs a
noiseless pipeline, retrieves qubit layouts, and can be configured to run noisy or device-specific pipelines as needed.
"""

from datetime import datetime

from src.pipelines import (
    PullaSettings,
    device_pipeline,
    get_layouts_from_layouts_info,
    noiseless_pipeline,
    noisy_pipeline,
    pulla_pipeline,
)


def main():
    print(f"{datetime.now()}: Start")
    # noiseless_pipeline()
    qubits_lists: list[list[int] | tuple[int, ...]]

    """
    qubits_lists = get_layouts_from_layouts_info(
        "data/noisy_1e4_shots/2026-07-27_203226_layouts_info.json"
    )
    """
    # qubits_lists = [(4, 5, 6)]  # Sirius
    qubits_lists = [(50, 43, 44)]  # Emerald
    # noisy_pipeline(qubits_lists)
    device_pipeline(qubits_lists)
    """
    settings: PullaSettings = PullaSettings(
        cz_amplitude_multiplier=None, measure_amplitude_multiplier=0.5, prx_amplitude_multiplier=None
    )

    pulla_pipeline(qubits_lists, settings)
    """
    print(f"{datetime.now()}: Done")


if __name__ == "__main__":
    main()
