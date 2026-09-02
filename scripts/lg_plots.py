import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

from src.pipelines import get_layouts_from_layouts_info

plt.rcParams["text.usetex"] = True
plt.rcParams["legend.loc"] = "lower right"

SYSTEM_NAME: str = "IQM Emerald"

DATA_FOLDER: str = os.environ["EXP_DATA_PATH"]
DATA_FILE_NAME: str = "lg_results_aggregated_summary.csv"
RESULTS_FILE_PATH: str = f"{DATA_FOLDER}\{DATA_FILE_NAME}"
# LAYOUTS: list[list[int]] = get_layouts_from_layouts_info(f"{DATA_FOLDER}/2026-08-19_022221_layouts_info.json")
LAYOUTS: list[list[int]] = [[4, 5, 6]]
LAYOUT_LABELS: list[str] = ["-".join([str(q) for q in layout]) for layout in LAYOUTS]
N_LAYOUTS: int = len(LAYOUTS)


def main() -> None:
    iv_LGBA = []
    ie_LGBA = []
    iv_LGAB = []
    ie_LGAB = []
    iv_AbC = []
    iv_bAC = []
    ie_AbC = []
    ie_bAC = []
    iv_aBC = []
    iv_BaC = []
    ie_aBC = []
    ie_BaC = []
    iv_ABC = []
    iv_BAC = []
    ie_ABC = []
    ie_BAC = []
    iv_Ab = []
    iv_bA = []
    ie_Ab = []
    ie_bA = []
    iv_aB = []
    iv_Ba = []
    ie_aB = []
    ie_Ba = []
    iv_abC = []
    iv_baC = []
    ie_abC = []
    ie_baC = []
    iv_AB = []
    iv_BA = []
    ie_AB = []
    ie_BA = []

    results_dataframe: pd.DataFrame = pd.read_csv(RESULTS_FILE_PATH, index_col=0)
    mv: float = 20.0

    iv_LGBA.append(results_dataframe.loc[:, "LGBA"])
    ie_LGBA.append(results_dataframe.loc[:, "LGeBA"])

    print(iv_LGBA[-1][0])
    print(ie_LGBA[-1][0])

    for ii in range(N_LAYOUTS):
        mv = min(mv, (iv_LGBA[-1][ii] - 1.0) / ie_LGBA[-1][ii])

    iv_LGAB.append(results_dataframe.loc[:, "LGAB"])
    ie_LGAB.append(results_dataframe.loc[:, "LGeAB"])

    for ii in range(N_LAYOUTS):
        mv = min(mv, (iv_LGAB[-1][ii] - 1) / ie_LGAB[-1][ii])

    iv_AbC.append(results_dataframe.loc[:, "AbC"])
    ie_AbC.append(results_dataframe.loc[:, "eAbC"])
    iv_bAC.append(results_dataframe.loc[:, "bAC"])
    ie_bAC.append(results_dataframe.loc[:, "ebAC"])
    iv_aBC.append(results_dataframe.loc[:, "aBC"])
    ie_aBC.append(results_dataframe.loc[:, "eaBC"])
    iv_BaC.append(results_dataframe.loc[:, "BaC"])
    ie_BaC.append(results_dataframe.loc[:, "eBaC"])
    iv_ABC.append(results_dataframe.loc[:, "ABC"])
    ie_ABC.append(results_dataframe.loc[:, "eABC"])
    iv_BAC.append(results_dataframe.loc[:, "BAC"])
    ie_BAC.append(results_dataframe.loc[:, "eBAC"])
    iv_Ab.append(results_dataframe.loc[:, "Ab"])
    ie_Ab.append(results_dataframe.loc[:, "eAb"])
    iv_bA.append(results_dataframe.loc[:, "bA"])
    ie_bA.append(results_dataframe.loc[:, "ebA"])
    iv_aB.append(results_dataframe.loc[:, "aB"])
    ie_aB.append(results_dataframe.loc[:, "eaB"])
    iv_Ba.append(results_dataframe.loc[:, "Ba"])
    ie_Ba.append(results_dataframe.loc[:, "eBa"])
    iv_abC.append(results_dataframe.loc[:, "abC"])
    ie_abC.append(results_dataframe.loc[:, "eabC"])
    iv_baC.append(results_dataframe.loc[:, "baC"])
    ie_baC.append(results_dataframe.loc[:, "ebaC"])
    iv_AB.append(results_dataframe.loc[:, "AB"])
    ie_AB.append(results_dataframe.loc[:, "eAB"])
    iv_BA.append(results_dataframe.loc[:, "BA"])
    ie_BA.append(results_dataframe.loc[:, "eBA"])
    print(mv)
    ddb: list[int] = list(range(N_LAYOUTS))

    _, ax = plt.subplots(1, 1, figsize=(5, 3), tight_layout=True)
    for q in range(1):
        # if q==0:
        ax.add_patch(Rectangle((-0.5, 0), N_LAYOUTS, 1, ec="none", fc="yellow", lw=0, label="_nolegend_"))
        ax.axhline(4 / 3, color="black", linewidth=0.5, label="_nolegend_")
        ax.errorbar(ddb, iv_LGAB[q], ie_LGAB[q], linewidth=0, capsize=3, elinewidth=1, marker=".", color="blue")
        ax.errorbar(ddb, iv_LGBA[q], ie_LGBA[q], linewidth=0, capsize=3, elinewidth=1, marker=".", color="red")
        ax.legend([r"$AB$", r"$BA$"])
        ax.set_ylim([0, 2])
        # if q>0:
        #    ax[q].set_ylim([0,1])
        # ax.set_xlim([-0.5, 9.5])
        ax.set_xlim([-0.5, N_LAYOUTS - 0.5])
        ax.set_xticks(ddb, LAYOUT_LABELS)
        ax.annotate(f"{SYSTEM_NAME}", xy=(0.5, 0.3), xycoords="axes fraction")
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        ax.tick_params("x", rotation=45, rotation_mode="xtick")
        ax.get_yaxis().get_offset_text().set_visible(False)

    plt.savefig(DATA_FOLDER + f"/lga_{SYSTEM_NAME}.pdf", bbox_inches="tight", pad_inches=0, dpi=300)
    plt.close()


if __name__ == "__main__":
    main()
