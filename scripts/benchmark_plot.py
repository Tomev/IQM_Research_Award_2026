"""TODO(TR): Docstring"""

import ast
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

plt.rcParams["text.usetex"] = True
plt.rcParams["legend.loc"] = "lower right"

SYSTEM_NAME: str = "iqm_emerald"
# SYSTEM_NAME: str = "iqm_sirius"

DATA_FOLDER: str = os.environ["EXP_DATA_PATH"]
DATA_FILE_NAME: str = "lg_results_aggregated_summary.csv"


def main() -> None:
    # Start with the simulator data

    # print(df)
    labels: list[str] = []
    lg_values: dict[str, list[float]] = {"AB": [], "BA": []}
    lg_errors: dict[str, list[float]] = {"AB": [], "BA": []}

    for prefix in ["sim", "gate"]:
        df: pd.DataFrame = pd.read_csv(f"{DATA_FOLDER}\{prefix}_{DATA_FILE_NAME}")

        for _, row in df.iterrows():
            labels.append(f"{prefix}-" + "-".join([str(q) for q in ast.literal_eval(row["qubits"])]))
            lg_values["AB"].append(row["LGAB"])
            lg_values["BA"].append(row["LGBA"])
            lg_errors["AB"].append(row["LGeAB"])
            lg_errors["BA"].append(row["LGeBA"])

    # Add gate results
    df: pd.DataFrame = pd.read_csv(f"{DATA_FOLDER}\gate_{DATA_FILE_NAME}")

    x_ticks: list[int] = list(range(len(labels)))

    _, ax = plt.subplots(1, 1, figsize=(5, 3), tight_layout=True)

    ax.add_patch(Rectangle((-0.5, 0), len(labels), 1, ec="none", fc="yellow", lw=0, label="_nolegend_"))
    ax.axhline(4 / 3, color="black", linewidth=0.5, label="_nolegend_")

    ax.errorbar(
        x_ticks, lg_values["AB"], lg_errors["AB"], linewidth=0, capsize=3, elinewidth=1, marker=".", color="blue"
    )
    ax.errorbar(
        x_ticks, lg_values["BA"], lg_errors["BA"], linewidth=0, capsize=3, elinewidth=1, marker=".", color="red"
    )
    ax.legend([r"$AB$", r"$BA$"])

    ax.set_xticks(x_ticks, labels)
    ax.tick_params("x", rotation=45, rotation_mode="xtick")

    plt.savefig(DATA_FOLDER + f"/benchmark_{SYSTEM_NAME}.pdf", bbox_inches="tight", pad_inches=0, dpi=300)
    plt.close()


if __name__ == "__main__":
    print(f"{datetime.now()}: Start")
    main()
    print(f"{datetime.now()}: End")
