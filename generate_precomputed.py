"""Rechnet die teure Studie vor (Build-Zeit, nicht in der App): `python generate_precomputed.py [Prozesse]` schreibt
`precomputed_sweep.json`.

  study  Spurzahl × Last × Stellplätze × Verteilung der Abfertigungsdauer: Verlustanteil (Mittel und Standardfehler aus je 3 Wiederholungen
         à 600 000 Ankünfte), mittlere Wartezeit der Angenommenen, Auslastung; Bezug: exakter Verlust bei exponentieller Dauer"""

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import erb_constants as C
from erb_evaluation import PRECOMPUTED_PATH, study_cell_run


def _task(args):
    c, rho_pct, k, kind, idx = args
    return study_cell_run(c, rho_pct, k, kind, C.STUDY_CUSTOMERS, seed=10_000 + 97 * idx, reps=C.STUDY_REPS)


def main(workers):
    t0 = time.time()
    jobs, idx = [], 0
    for c in C.STUDY_C:
        for rho_pct in C.STUDY_RHO_PCT:
            for k in C.STUDY_K:
                for kind in C.STUDY_KINDS:
                    jobs.append((c, rho_pct, k, kind, idx))
                    idx += 1
    with ProcessPoolExecutor(max_workers=workers) as ex:
        study = list(ex.map(_task, jobs))
    out = {"study_customers": C.STUDY_CUSTOMERS, "study_reps": C.STUDY_REPS, "warmup_fraction": C.WARMUP_FRACTION, "study": study}
    Path(PRECOMPUTED_PATH).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"fertig in {time.time() - t0:.0f} s -> {PRECOMPUTED_PATH}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else min(6, os.cpu_count() or 1))
