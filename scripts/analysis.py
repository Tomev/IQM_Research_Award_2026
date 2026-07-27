import os
from math import sin, sqrt

import pandas as pd

from src.pipelines import get_layouts_from_layouts_info

# Settings
N_JOBS_PER_LAYOUT: int = 5
N_STEERIING_BITS: int = 8

STATES_ORDER = ["000", "100", "010", "110", "001", "101", "011", "111"]
COLUMNS: list[str] = [
    "qubits",
    "LGBA",
    "LGeBA",
    "LGAB",
    "LGeAB",
    "ABC",
    "eABC",
    "BAC",
    "eBAC",
    "AbC",
    "eAbC",
    "bAC",
    "ebAC",
    "BaC",
    "eBaC",
    "aBC",
    "eaBC",
    "abC",
    "eabC",
    "baC",
    "ebaC",
    "AB",
    "eAB",
    "BA",
    "eBA",
    "Ab",
    "eAb",
    "bA",
    "ebA",
    "Ba",
    "eBa",
    "aB",
    "eaB",
]


LAYOUTS = get_layouts_from_layouts_info("./data/noisy_1e4_shots/2026-07-27_203226_layouts_info.json")
DATA_FOLDER: str = os.environ["EXP_DATA_PATH"]


class LGResult:
    def __init__(self, results_table: pd.DataFrame) -> None:
        self.raw_results = results_table

    def AppendResults(self, result: pd.DataFrame) -> None:
        self.raw_results = pd.concat([self.raw_results, pd.DataFrame(result)], ignore_index=True)

    def Calculate(self, qubit_set_idx):
        b = []
        for steering_bit in range(N_STEERIING_BITS):
            a = []
            selected_row = self.raw_results.loc[
                (self.raw_results["qubits_set_index"] == qubit_set_idx) & (self.raw_results["i"] == steering_bit)
            ]
            for state in STATES_ORDER:
                # print(state)
                # print(selected_row)
                # print(selected_row[state].to_numpy())
                a.append(selected_row[state].to_numpy()[0])

            b.append(a)

        return b

    def SumResults(self) -> None:
        # i denotes steering_bit "value"
        self.raw_results = self.raw_results.groupby(["i", "qubits_set_index"], as_index=False).sum()


def main():

    aggregated_df: pd.DataFrame = pd.DataFrame(columns=COLUMNS)

    for layout_index in range(len(LAYOUTS)):
        print(layout_index)

        summed_result = LGResult(pd.DataFrame())

        for i in range(N_JOBS_PER_LAYOUT):
            pd_result = pd.read_csv(f"{DATA_FOLDER}/results_tests_{i + N_JOBS_PER_LAYOUT * layout_index}.csv")

            summed_result.AppendResults(pd_result)

            raw_results = LGResult(pd.DataFrame())
            raw_results.AppendResults(pd_result)

            raw_results.SumResults()

        summed_result.SumResults()

        weak_meas_rotation_angle_v = 0.1  # That's our weak measurement rotation angle.
        weak_meas_rotation_angle = sin(weak_meas_rotation_angle_v)

        inequality_values_AB = []
        inequality_values_BA = []
        inequality_values_AbC = []
        inequality_values_bAC = []
        inequality_values_BaC = []
        inequality_values_aBC = []
        inequality_errors_AB = []
        inequality_errors_BA = []
        inequality_errors_AbC = []
        inequality_errors_bAC = []
        inequality_errors_BaC = []
        inequality_errors_aBC = []
        order = []
        eorder = []
        val_abC = []
        val_baC = []
        er_abC = []
        er_baC = []
        val_AB = []
        val_BA = []
        er_AB = []
        er_BA = []
        val_ABC = []
        val_BAC = []
        er_ABC = []
        er_BAC = []
        val_BaC = []
        val_aBC = []
        er_BaC = []
        er_aBC = []
        val_AbC = []
        val_bAC = []
        er_AbC = []
        er_bAC = []
        val_Ab = []
        val_bA = []
        er_Ab = []
        er_bA = []
        val_aB = []
        val_Ba = []
        er_aB = []
        er_Ba = []

        qubs = []
        # inequality_values_mean = []
        counts_per_steering_bit = summed_result.Calculate(0)

        n_shots = 0

        for measured_state_idx in range(N_STEERIING_BITS):
            n_shots += counts_per_steering_bit[0][measured_state_idx]

        print("Qubit_set_index:", layout_index)
        print("Trials: ", n_shots)

        # print(counts_per_steering_bit)

        ss = []
        ac = []
        ab = []
        bc = []
        aa = []
        bb = []
        c = []
        print("xxC")

        for steering_bit in range(N_STEERIING_BITS):
            sc = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
            )
            s = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
            )
            sac = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
            )

            sbc = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
            )
            sab = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("001")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("101")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("011")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("111")]
            )
            sa = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("001")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("101")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("011")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("111")]
            )
            sb = (
                +counts_per_steering_bit[steering_bit][STATES_ORDER.index("000")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("100")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("010")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("110")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("001")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("101")]
                + counts_per_steering_bit[steering_bit][STATES_ORDER.index("011")]
                - counts_per_steering_bit[steering_bit][STATES_ORDER.index("111")]
            )
            c.append(sc)
            ss.append(s)
            ac.append(sac)
            ab.append(sab)
            bc.append(sbc)
            aa.append(sa)
            bb.append(sb)

        # Indices in the equations below denote the value of steering_bits of the run.
        # All the ss, ac, ab, bc, aa, bb have 8 elements.

        # For steering_qubit in [0, 3], the weak measurements order is A B, hence
        # we only use 0-3 indices in the equations below.
        print("baC")
        baC = (c[0] + c[3] + c[2] + c[1]) / (n_shots * 4)
        ebaC = (c[0] + c[3] + c[2] + c[1]) / (n_shots) - (c[0] ** 2 + c[3] ** 2 + c[2] ** 2 + c[1] ** 2) / (
            n_shots
        ) ** 2
        print(baC, sqrt(ebaC / n_shots) / 4)
        print("abC")
        abC = (c[4] + c[7] + c[6] + c[5]) / (n_shots * 4)
        eabC = (c[4] + c[7] + c[6] + c[5]) / n_shots - (c[4] ** 2 + c[7] ** 2 + c[6] ** 2 + c[5] ** 2) / (n_shots) ** 2
        print(abC, sqrt(eabC / n_shots) / 4)
        print("BAC")
        BAC = (ss[0] + ss[3] - ss[2] - ss[1]) / (n_shots * weak_meas_rotation_angle * weak_meas_rotation_angle * 4)
        eBAC = (c[0] + c[3] + c[2] + c[1]) / (n_shots) - (ss[0] ** 2 + ss[3] ** 2 + ss[2] ** 2 + ss[1] ** 2) / (
            n_shots
        ) ** 2
        print(BAC, sqrt(eBAC / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        print("ABC")
        ABC = (ss[4] + ss[7] - ss[6] - ss[5]) / (n_shots * weak_meas_rotation_angle * weak_meas_rotation_angle * 4)
        eABC = (c[4] + c[7] + c[6] + c[5]) / n_shots - (ss[4] ** 2 + ss[7] ** 2 + ss[6] ** 2 + ss[5] ** 2) / (
            n_shots
        ) ** 2
        print(ABC, sqrt(eABC / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        print("BA")
        BA = (ab[0] + ab[3] - ab[2] - ab[1]) / (n_shots * weak_meas_rotation_angle * weak_meas_rotation_angle * 4)
        eBA = 4 - (ab[0] ** 2 + ab[3] ** 2 + ab[2] ** 2 + ab[1] ** 2) / (n_shots) ** 2
        print(BA, sqrt(eBA / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        print("AB")
        AB = (ab[4] + ab[7] - ab[6] - ab[5]) / (n_shots * weak_meas_rotation_angle * weak_meas_rotation_angle * 4)
        eAB = 4 - (ab[4] ** 2 + ab[7] ** 2 + ab[6] ** 2 + ab[5] ** 2) / (n_shots) ** 2
        print(AB, sqrt(eAB / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        print("bAC")
        bAC = -(ac[0] - ac[3] + ac[2] - ac[1]) / (n_shots * weak_meas_rotation_angle * 4)
        ebAC = (c[0] + c[3] + c[2] + c[1]) / (n_shots) - (ac[0] ** 2 + ac[3] ** 2 + ac[2] ** 2 + ac[1] ** 2) / (
            n_shots
        ) ** 2
        print(bAC, sqrt(ebAC / n_shots) / (4 * weak_meas_rotation_angle))
        print("AbC")
        AbC = -(ac[4] - ac[7] + ac[6] - ac[5]) / (n_shots * weak_meas_rotation_angle * 4)
        eAbC = (c[4] + c[7] + c[6] + c[5]) / n_shots - (ac[4] ** 2 + ac[7] ** 2 + ac[6] ** 2 + ac[5] ** 2) / (
            n_shots
        ) ** 2
        print(AbC, sqrt(eAbC / n_shots) / (4 * weak_meas_rotation_angle))
        print("BaC")
        BaC = -(bc[0] - bc[3] - bc[2] + bc[1]) / (n_shots * weak_meas_rotation_angle * 4)
        eBaC = (c[0] + c[3] + c[2] + c[1]) / (n_shots) - (bc[0] ** 2 + bc[3] ** 2 + bc[2] ** 2 + bc[1] ** 2) / (
            n_shots
        ) ** 2
        print(BaC, sqrt(eBaC / n_shots) / (4 * weak_meas_rotation_angle))
        print("aBC")
        aBC = -(bc[4] - bc[7] - bc[6] + bc[5]) / (n_shots * weak_meas_rotation_angle * 4)
        eaBC = (c[4] + c[7] + c[6] + c[5]) / n_shots - (bc[4] ** 2 + bc[7] ** 2 + bc[6] ** 2 + bc[5] ** 2) / (
            n_shots
        ) ** 2
        print(aBC, sqrt(eaBC / n_shots) / (4 * weak_meas_rotation_angle))
        print("bA")
        bA = -(aa[0] - aa[3] + aa[2] - aa[1]) / (n_shots * weak_meas_rotation_angle * 4)
        ebA = 4 - (aa[0] ** 2 + aa[3] ** 2 + aa[2] ** 2 + aa[1] ** 2) / (n_shots) ** 2
        print(bA, sqrt(ebA / n_shots) / (4 * weak_meas_rotation_angle))
        print("Ab")
        Ab = -(aa[4] - aa[7] + aa[6] - aa[5]) / (n_shots * weak_meas_rotation_angle * 4)
        eAb = 4 - (aa[4] ** 2 + aa[7] ** 2 + aa[6] ** 2 + aa[5] ** 2) / (n_shots) ** 2
        print(Ab, sqrt(eAb / n_shots) / (4 * weak_meas_rotation_angle))
        print("Ba")
        Ba = -(bb[0] - bb[3] - bb[2] + bb[1]) / (n_shots * weak_meas_rotation_angle * 4)
        eBa = 4 - (bb[0] ** 2 + bb[3] ** 2 + bb[2] ** 2 + bb[1] ** 2) / (n_shots) ** 2
        print(Ba, sqrt(eBa / n_shots) / (4 * weak_meas_rotation_angle))
        print("aB")
        aB = -(bb[4] - bb[7] - bb[6] + bb[5]) / (n_shots * weak_meas_rotation_angle * 4)
        eaB = 4 - (bb[4] ** 2 + bb[7] ** 2 + bb[6] ** 2 + bb[5] ** 2) / (n_shots) ** 2
        print(aB, sqrt(eaB / n_shots) / (4 * weak_meas_rotation_angle))
        qubs.append(LAYOUTS[layout_index])
        wBA = (bAC + BaC) ** 2 / (4 * baC * BAC)
        wAB = (AbC + aBC) ** 2 / (4 * abC * ABC)
        inequality_values_BA.append(wBA)
        inequality_values_AB.append(wAB)
        inequality_errors_BA.append(
            (bAC + BaC) ** 2
            * sqrt(eBAC / n_shots)
            / (baC * 16 * weak_meas_rotation_angle * weak_meas_rotation_angle * BAC**2)
        )
        inequality_errors_AB.append(
            (AbC + aBC) ** 2
            * sqrt(eABC / n_shots)
            / (abC * 16 * weak_meas_rotation_angle * weak_meas_rotation_angle * ABC**2)
        )
        val_abC.append(abC)
        val_baC.append(baC)
        er_abC.append(sqrt(eabC / n_shots) / (4))
        er_baC.append(sqrt(ebaC / n_shots) / (4))
        val_AB.append(AB)
        val_BA.append(BA)
        er_AB.append(sqrt(eAB / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        er_BA.append(sqrt(eBA / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        val_ABC.append(ABC)
        val_BAC.append(BAC)
        er_ABC.append(sqrt(eABC / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        er_BAC.append(sqrt(eBAC / n_shots) / (4 * weak_meas_rotation_angle * weak_meas_rotation_angle))
        val_BaC.append(BaC)
        val_aBC.append(aBC)
        er_BaC.append(sqrt(eBaC / n_shots) / (4 * weak_meas_rotation_angle))
        er_aBC.append(sqrt(eaBC / n_shots) / (4 * weak_meas_rotation_angle))
        val_AbC.append(AbC)
        val_bAC.append(bAC)
        er_AbC.append(sqrt(eAbC / n_shots) / (4 * weak_meas_rotation_angle))
        er_bAC.append(sqrt(ebAC / n_shots) / (4 * weak_meas_rotation_angle))
        val_Ab.append(Ab)
        val_bA.append(bA)
        er_Ab.append(sqrt(eAb / n_shots) / (4 * weak_meas_rotation_angle))
        er_bA.append(sqrt(ebA / n_shots) / (4 * weak_meas_rotation_angle))
        val_aB.append(aB)
        val_Ba.append(Ba)
        er_aB.append(sqrt(eaB / n_shots) / (4 * weak_meas_rotation_angle))
        er_Ba.append(sqrt(eBa / n_shots) / (4 * weak_meas_rotation_angle))

        indices = range(len(inequality_values_AB))

        df = pd.DataFrame(
            columns=COLUMNS,
            index=indices,
        )

        for i in indices:
            df.loc[i, "qubits"] = qubs[i]
            df.loc[i, "LGBA"] = inequality_values_BA[i]
            df.loc[i, "LGeBA"] = inequality_errors_BA[i]
            df.loc[i, "LGAB"] = inequality_values_AB[i]
            df.loc[i, "LGeAB"] = inequality_errors_AB[i]
            df.loc[i, "BA"] = val_BA[i]
            df.loc[i, "eBA"] = er_BA[i]
            df.loc[i, "AB"] = val_AB[i]
            df.loc[i, "eAB"] = er_AB[i]
            df.loc[i, "BaC"] = val_BaC[i]
            df.loc[i, "eBaC"] = er_BaC[i]
            df.loc[i, "aBC"] = val_aBC[i]
            df.loc[i, "eaBC"] = er_aBC[i]
            df.loc[i, "bAC"] = val_bAC[i]
            df.loc[i, "ebAC"] = er_bAC[i]
            df.loc[i, "AbC"] = val_AbC[i]
            df.loc[i, "eAbC"] = er_AbC[i]
            df.loc[i, "BAC"] = val_BAC[i]
            df.loc[i, "eBAC"] = er_BAC[i]
            df.loc[i, "ABC"] = val_ABC[i]
            df.loc[i, "eABC"] = er_ABC[i]
            df.loc[i, "baC"] = val_baC[i]
            df.loc[i, "ebaC"] = er_baC[i]
            df.loc[i, "abC"] = val_abC[i]
            df.loc[i, "eabC"] = er_abC[i]
            df.loc[i, "Ba"] = val_Ba[i]
            df.loc[i, "eBa"] = er_Ba[i]
            df.loc[i, "aB"] = val_aB[i]
            df.loc[i, "eaB"] = er_aB[i]
            df.loc[i, "bA"] = val_bA[i]
            df.loc[i, "ebA"] = er_bA[i]
            df.loc[i, "Ab"] = val_Ab[i]
            df.loc[i, "eAb"] = er_Ab[i]

        aggregated_df = pd.concat([aggregated_df, df], axis=0)
        df.to_csv(f"{DATA_FOLDER}/lg_results_summary_layout_{LAYOUTS[layout_index]}.csv")

    aggregated_df.to_csv(f"{DATA_FOLDER}/lg_results_aggregated_summary.csv")


if __name__ == "__main__":
    main()
