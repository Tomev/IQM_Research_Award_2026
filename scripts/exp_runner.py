"""
This script serves as the main entry point for executing quantum computing pipelines. It initializes the process, runs a
noiseless pipeline, retrieves qubit layouts, and can be configured to run noisy or device-specific pipelines as needed.
"""

from datetime import datetime

from src.pipelines import device_pipeline, get_layouts_from_layouts_info, noiseless_pipeline, noisy_pipeline


def main():
    print(f"{datetime.now()}: Start")
    noiseless_pipeline()
    qubits_lists: list[list[int] | tuple[int, ...]] = get_layouts_from_layouts_info("")
    # noisy_pipeline(qubits_lists)
    # device_pipeline(qubits_lists)
    print(f"{datetime.now()}: Done")


if __name__ == "__main__":
    main()
