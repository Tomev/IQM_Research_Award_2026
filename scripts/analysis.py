import os
from math import sin, sqrt

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from src.pipelines import get_layouts_from_layouts_info

# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------

DATA_FOLDER: str = os.environ["EXP_DATA_PATH"]

# LAYOUTS: list[list[int]] = [[4, 5, 6]]
LAYOUTS: list[list[int]] = [[0, 1, 2]]
# LAYOUTS = get_layouts_from_layouts_info(f"{DATA_FOLDER}/2026-07-27_203226_layouts_info.json")

N_LAYOUTS: int = len(LAYOUTS)
# N_LAYOUTS = 1
N_JOBS_PER_LAYOUT: int = 10
N_STEERING_BITS: int = 8
N_LAYOUTS_PER_JOB: int = 1


WEAK_ANGLE: float = 0.1
LAM: float = sin(WEAK_ANGLE)

STATES_ORDER: list[str] = ["000", "100", "010", "110", "001", "101", "011", "111"]

# steering-bit groups.
GROUPS: dict[str, tuple[int, ...]] = {"BA": (0, 3, 2, 1), "AB": (4, 7, 6, 5)}


class LGResults:
    def __init__(self, results_table: pd.DataFrame) -> None:
        self.raw_results: pd.DataFrame = results_table

    def append_results(self, result: pd.DataFrame) -> None:
        self.raw_results = pd.concat([self.raw_results, pd.DataFrame(result)], ignore_index=True)

    def calculate(self, qubit_set_idx) -> NDArray[np.floating]:
        b: list[list[NDArray]] = []
        for steering_bit in range(N_STEERING_BITS):
            a: list[NDArray] = []
            selected_row: pd.DataFrame = self.raw_results.loc[
                (self.raw_results["qubits_set_index"] == qubit_set_idx) & (self.raw_results["i"] == steering_bit)
            ]
            for state in STATES_ORDER:
                # print(selected_row)
                # print(qubit_set_idx)
                # print(steering_bit)
                a.append(selected_row[state].to_numpy()[0])
            b.append(a)
        return np.asarray(b, dtype=float)

    def sum_results(self) -> None:
        self.raw_results = self.raw_results.groupby(["i", "qubits_set_index"], as_index=False).sum()


# ---------------------------------------------------------------------------
# per-steering-bit sums
# ---------------------------------------------------------------------------


def steering_sums(counts):
    """counts: (8 steering bits) x (8 states).  Returns the seven sums."""
    i: dict[str, int] = {s: STATES_ORDER.index(s) for s in STATES_ORDER}
    k000, k100, k010, k110 = i["000"], i["100"], i["010"], i["110"]
    k001, k101, k011, k111 = i["001"], i["101"], i["011"], i["111"]
    n = counts

    return dict(
        c=n[:, k000] + n[:, k100] + n[:, k010] + n[:, k110],
        ss=n[:, k000] - n[:, k100] - n[:, k010] + n[:, k110],
        ac=n[:, k000] + n[:, k100] - n[:, k010] - n[:, k110],
        bc=n[:, k000] - n[:, k100] + n[:, k010] - n[:, k110],
        ab=(n[:, k000] - n[:, k100] - n[:, k010] + n[:, k110] + n[:, k001] - n[:, k101] - n[:, k011] + n[:, k111]),
        aa=(n[:, k000] + n[:, k100] - n[:, k010] - n[:, k110] + n[:, k001] + n[:, k101] - n[:, k011] - n[:, k111]),
        bb=(n[:, k000] - n[:, k100] + n[:, k010] - n[:, k110] + n[:, k001] - n[:, k101] + n[:, k011] - n[:, k111]),
    )


# contrast patterns, written on the ordered group (k0, k3, k2, k1)
_DOUBLE = np.array([+1.0, +1.0, -1.0, -1.0])  # ss, ab   -> lambda^2
_FLAT = np.array([+1.0, +1.0, +1.0, +1.0])  # c        -> lambda^0
_CONTR_A = np.array([-1.0, +1.0, -1.0, +1.0])  # ac, aa   -> lambda   (A sign)
_CONTR_B = np.array([-1.0, +1.0, +1.0, -1.0])  # bc, bb   -> lambda   (B sign)


def observables(counts, lam=LAM):
    """
    All fourteen quantities and their errors, keyed by the column names of
    results-*.csv.  Errors are the same Bernoulli expressions as before:
    for a variable X with X**2 = 1_c the per-setting variance is p_k - m_k**2,
    for X**2 = 1 it is 1 - m_k**2.
    """
    s = steering_sums(counts)
    n_shots: int = counts[0].sum()
    out = {}

    for order, g in GROUPS.items():
        g = list(g)
        p = s["c"][g] / n_shots  # P(c=1) per setting
        # names: (column, source array, contrast, power of lambda, X**2 is 1_c?)
        spec = [
            ("abC" if order == "AB" else "baC", "c", _FLAT, 0, True),
            ("ABC" if order == "AB" else "BAC", "ss", _DOUBLE, 2, True),
            ("AB" if order == "AB" else "BA", "ab", _DOUBLE, 2, False),
            ("AbC" if order == "AB" else "bAC", "ac", _CONTR_A, 1, True),
            ("aBC" if order == "AB" else "BaC", "bc", _CONTR_B, 1, True),
            ("Ab" if order == "AB" else "bA", "aa", _CONTR_A, 1, False),
            ("aB" if order == "AB" else "Ba", "bb", _CONTR_B, 1, False),
        ]
        for col, arr, sign, power, conditional in spec:
            m = s[arr][g] / n_shots
            out[col] = float((sign * m).sum() / (4 * lam**power))
            var = (p - m**2).sum() if conditional else (4.0 - (m**2).sum())
            out["e" + col] = float(sqrt(var / n_shots) / (4 * lam**power))

    out["n_shots"] = n_shots
    return out


# ---------------------------------------------------------------------------
# Eq. (11), product form
# ---------------------------------------------------------------------------

COLS: dict[str, dict[str, str]] = {
    "AB": dict(a="Ab", b="aB", ac="AbC", bc="aBC", ab="AB", abc="ABC", c="abC"),
    "BA": dict(a="bA", b="Ba", ac="bAC", bc="BaC", ab="BA", abc="BAC", c="baC"),
}


def w11(obs, order: str):
    """<ac><bc>/(<c><abc>); error from the <abc> term only, as before."""
    k: dict[str, str] = COLS[order]
    w = obs[k["ac"]] * obs[k["bc"]] / (obs[k["c"]] * obs[k["abc"]])
    return w, abs(w) * obs["e" + k["abc"]] / abs(obs[k["abc"]])


# ---------------------------------------------------------------------------
# Eq. (12)
# ---------------------------------------------------------------------------


def d12(obs, order: str):
    """the bare statistic  <a><bc> - <b><ac>  (units lambda^-2)"""
    k: dict[str, str] = COLS[order]
    return obs[k["a"]] * obs[k["bc"]] - obs[k["b"]] * obs[k["ac"]]


def eq12_propagated(obs, order):
    """D, its independent-error propagation, and the two gain ratios."""
    k = COLS[order]
    a, b = obs[k["a"]], obs[k["b"]]
    ac, bc = obs[k["ac"]], obs[k["bc"]]
    r_A = a - ac
    r_B = b - bc
    ea, eb = obs["e" + k["a"]], obs["e" + k["b"]]
    eac, ebc = obs["e" + k["ac"]], obs["e" + k["bc"]]

    D = a * bc - b * ac
    S = a * bc + b * ac
    eD = sqrt((bc * ea) ** 2 + (a * ebc) ** 2 + (ac * eb) ** 2 + (b * eac) ** 2)
    r_dir, r_cond = a / b, ac / bc
    return dict(
        D=D,
        eD=eD,
        nsig=D / eD if eD else np.nan,
        rel=2 * D / (a * bc + b * ac),
        r_dir=r_dir,
        er_dir=abs(r_dir) * sqrt((ea / a) ** 2 + (eb / b) ** 2),
        r_cond=r_cond,
        er_cond=abs(r_cond) * sqrt((eac / ac) ** 2 + (ebc / bc) ** 2),
        nsig_a_eq_b=(a - b) / np.hypot(ea, eb),
        nsig_ac_eq_bc=(ac - bc) / np.hypot(eac, ebc),
        S=S,
    )


def eq12_pooled(job_counts, order, lam=LAM):
    """
    Version A.  Sum the jobs, form the averages, then D.
    """
    job_counts = [np.asarray(c, dtype=float) for c in job_counts]
    J = len(job_counts)
    total = sum(job_counts)
    D_full = d12(observables(total, lam), order)

    obs = observables(total, lam)
    p = eq12_propagated(obs, order)
    return dict(D=D_full, err=p["eD"], method="pooled", n_jobs=J, S=p["S"])


def eq12_perjob(job_counts, order, lam=LAM):
    """
    Version B.  D_j in each job, then the plain mean.
    """
    job_counts = [np.asarray(c, dtype=float) for c in job_counts]
    J = len(job_counts)
    per = [eq12_propagated(observables(c, lam), order) for c in job_counts]
    D_j = np.array([p["D"] for p in per])
    e_j = np.array([p["eD"] for p in per])

    Dbar = D_j.mean()
    err = np.sqrt(sum(e_j[i] ** 2 for i in range(J))) / J
    return dict(D=Dbar, err=err, method="mean over jobs", n_jobs=J)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(results_dir=DATA_FOLDER, lam=LAM):
    # n_jobs: int = len(LAYOUTS) * N_JOBS_PER_LAYOUT

    job_index: int = 0
    all_rows: list = []

    for q in range(len(LAYOUTS)):
        per_job = []
        summed = LGResults(pd.DataFrame())

        for _ in range(N_JOBS_PER_LAYOUT):
            pd_result = pd.read_csv(f"{results_dir}/results_tests_{job_index}.csv", index_col=0)
            summed.append_results(pd_result)
            one = LGResults(pd.DataFrame())
            one.append_results(pd_result)
            one.sum_results()
            per_job.append(one)
            job_index += 1
        summed.sum_results()

        rows = []

        # for q in range(len(LAYOUTS)):
        pooled_counts = summed.calculate(0)
        job_counts = [pj.calculate(0) for pj in per_job]

        obs = observables(pooled_counts, lam)
        row = {"qubits": LAYOUTS[q]}

        for order in ("AB", "BA"):
            w, ew = w11(obs, order)
            prop = eq12_propagated(obs, order)
            pooled = eq12_pooled(job_counts, order, lam)
            perjob = eq12_perjob(job_counts, order, lam)

            tag: str = "LG" + order
            row[tag] = w
            row["LGe" + order] = ew
            row["D" + order] = pooled["D"]
            row["S" + order] = pooled["S"]
            row["eD" + order] = pooled["err"]
            # print(f"Set {q} order {order}:   Eq.(11)   {w:+.3e} +- {ew:.1e}"
            #      f"  ({(w-1)/ew:+.2f} sigma, )")
            # row["D12job" + order] = perjob["D"]
            # row["eD12job" + order] = perjob["err"]
            print(
                f"Set {q} order {order}:   Eq.(12) pooled  {pooled['D']:+.3e} +- {pooled['err']:.1e}"
                f"  ({pooled['D'] / pooled['err']:+.2f} sigma, {pooled['method']})"
            )
            # print(f"      Eq.(12) per-job {perjob['D']:+.3e} +- {perjob['err']:.1e}"
            #      f"  ({perjob['D']/perjob['err']:+.2f} sigma)")
        row.update({k: v for k, v in obs.items() if k != "n_shots"})
        rows.append(row)
        all_rows.extend(rows)

        df: pd.DataFrame = pd.DataFrame(rows)
        df.to_csv(f"{results_dir}/lg_results_{LAYOUTS[q]}_summary.csv")

    df: pd.DataFrame = pd.DataFrame(all_rows)
    df.to_csv(f"{results_dir}/lg_results_aggregated_summary.csv")


if __name__ == "__main__":
    main()
