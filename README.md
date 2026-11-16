# Confirmation-gate audit kit (paper #236)

Companion kit for *When the Verifier Becomes the Objective: A Verification Envelope for Self-Evolving
Research Agents* (NeurIPS 2026 workshop "Who Verifies the Agents?", OpenReview #236). It reproduces the
paper's post-acceptance results on the holdout confirmation gate: Appendix H (Tables 8-11, Figure 2), the
sequential gate included, and the continuity check against Table 7.

**Status: public release v1.1.0 (16 November 2026).** This kit is the paper's runnable artifact.
It reproduces the gate's calibration and repair results only. The audited system itself is not released, and
the paper's mutation audit, blind mutation campaign, and holdout-reuse and seed-map counts cannot be rerun from
this kit (see *What is not inside*).
**License:** MIT (see `LICENSE`).

## What is inside

| File | What it is |
|---|---|
| `frozen_rule.py` | The audited gate's **decision rule**, written for this kit from the paper's Appendix E (standard library). It is the flawed rule under audit: use it to reproduce, never to certify. `PROVENANCE.md` gives the evidence that it returns the audited code's outcomes. |
| `strict_mean_gate.py` | The repaired gate (contract `paper236-strict-gate-1.0`), in the kit's edition: the decision function is the evaluated one, and the betting-fraction arithmetic is written anew, because the evaluated file had taken it from the audited system. |
| `sequential_mean_gate.py` | The sequential gate (contract `paper236-sequential-gate-1.0`): the strict gate's e-process read one value at a time, stopping at the first confirmation or after a budget fixed in advance. Also the kit's edition, for the same reason. |
| `evaluated_values.py` | Checks the kit's two gates against values recorded from the evaluated gate files on 4,000 seeded bands (`reference_results/evaluated_gate_values.json`), and prints `PASSED` or `FAILED`. |
| `protocol.json` | The pre-registered comparison: 12 distributions, 10 band sizes, 20 edge cases, criteria C1-C6, the power-reporting rule. Committed before the strict gate's code and before any run; no amendments. |
| `protocol_sequential.json` | The pre-registered sequential comparison: the same 12 distributions, budgets 8-200, 10,000 streams of 200 values per distribution, 15 edge cases, criteria S1-S6. Committed before the sequential gate's code and before any run; no amendments. |
| `run_protocol.py` | Runs the protocol with this kit's files only: identical seeded bands go to the frozen rule (three configurations) and to the strict gate. |
| `compare_to_reference.py` | Checks a run band by band against `reference_results/` and prints `PASSED` or `FAILED`. |
| `summarize.py` | Recomputes every rate, Wilson interval and criterion from the raw outcome codes. |
| `run_sequential.py`, `summarize_sequential.py` | The authors' runner and summarizer for the sequential comparison, byte-identical to the versions that produced the reference run. Each stream goes to the sequential gate and its first N values to the fixed-band strict gate. |
| `compare_sequential.py` | Checks a sequential run stream by stream against `reference_results/sequential/` and prints `PASSED` or `FAILED`. |
| `reference_results/sequential/` | The authors' single run of `protocol_sequential.json`, with the evaluated gate files (hashes in `run_meta_sequential.json`). |
| `reference_results/` | The authors' run against the **audited code** (not included; two report-only functions were replaced by constants for speed, as registered in `protocol.json`), the Table 7 replay (`table7_calibration_results.json`) and the values recorded from the evaluated gate files. |
| `make_paper_assets.py`, `make_sequential_table.py` | The authors' generators of the paper's Table 10 rows, Figure 2's coordinates and quoted numbers, and of Table 11's rows, byte-identical to the versions that produced the paper's tables. Exact ties at the third decimal round half up. |
| `tests/test_kit.py` | Seventeen regression tests (under a second): nine for the frozen rule and the strict gate, six for the sequential gate, two for the betting fractions against the formula printed in Appendix E. |

## What is not inside

No file of the audited system; no orchestration, prompts or research policy; no live holdout instances or
seeds; no credentials. All seeds here are simulation seeds.

Three things connect the kit to the audited system, and `PROVENANCE.md` describes each:
- `frozen_rule.py` and the two gates implement the formulas of the paper's Appendices E and H, as the audited
  code does. They were written with an AI coding assistant, in a session that had read that code. A
  statement-by-statement comparison finds no statement of it in them beyond generic ones such as `import math`;
  an independent review found a few smaller fragments, which `PROVENANCE.md` lists (*Statement comparison*).
- The two gate files are not the files evaluated for the paper, which carried a function of the audited
  system. They are checked against the evaluated files' recorded results (`evaluated_values.py` and both
  protocols).
- `protocol.json`, `protocol_sequential.json` and the reference results are kept byte-identical, so they name
  a few of the audited system's files and functions, its branch labels and one environment setting.

## Commands

Run from this directory. Only the standard library is used; `-I -S` keeps the run isolated from
site-packages and environment variables. Tested with CPython 3.14.2 (every command) and 3.12.10 (the tests,
`evaluated_values.py` and the quick checks) on Windows 11. The same commands
are in `.github/workflows/reproduce.yml` for Linux, Windows and macOS; that workflow runs on demand
and has not yet run in this repository.

```sh
python -I -S -m unittest discover -s tests -v        # 17 tests, under a second
python -I -S evaluated_values.py                     # the kit's gates against the evaluated files' recorded values; expect PASSED
python -I -S run_protocol.py --cells 3               # quick check: the first 3 cells
python -I -S compare_to_reference.py                 # checks only the cells present in results/
python -I -S run_protocol.py                         # full protocol: 120 cells, about 1.5 minutes on one core
python -I -S compare_to_reference.py                 # expect: compared 120 cells (384000 bands x 4 gates) and 20 edge cases / PASSED
python -I -S summarize.py --protocol protocol.json --raw results --table7 reference_results/table7_calibration_results.json
```

`summarize.py` writes `results/summary.json` and `results/summary.md`; every criterion C1-C6 should
read PASS. Without `--table7`, C6 is reported as not evaluated.

The sequential gate (Table 11):

```sh
python -I -S run_sequential.py --base protocol.json --protocol protocol_sequential.json --sequential sequential_mean_gate.py --strict strict_mean_gate.py --out results_sequential_quick --streams 500   # quick check, seconds
python -I -S compare_sequential.py --results results_sequential_quick   # checks the first 500 streams of every cell
python -I -S run_sequential.py --base protocol.json --protocol protocol_sequential.json --sequential sequential_mean_gate.py --strict strict_mean_gate.py --out results_sequential   # full protocol: 72 cells, 1.5-2 minutes on one core
python -I -S compare_sequential.py                  # expect: compared 72 of 72 cells (72 full, 720000 streams x 2 gates), 15 edge cases and 3 argument errors / PASSED
python -I -S summarize_sequential.py --base protocol.json --protocol protocol_sequential.json --raw results_sequential
```

`summarize_sequential.py` writes `summary_sequential.json` and `summary_sequential.md` into
`results_sequential`; every criterion S1-S6 should read PASS. `compare_sequential.py` also prints the
hashes of the two gate files: they are the kit's editions, so they differ from the reference run's.

The paper's tables from your own runs (after the two `summarize` commands above):

```sh
python -I -S make_paper_assets.py --summary results/summary.json --out results     # Table 10 rows, Figure 2 coordinates, quoted numbers
python -I -S make_sequential_table.py results_sequential/summary_sequential.json results_sequential/sequential_table.tex   # Table 11 rows
```

`results/repair_table.tex`, `results/repair_figure.tex` and `results_sequential/sequential_table.tex` should
match the paper's Tables 10 and 11 and Figure 2 exactly; `results/repair_numbers.json` holds the quoted numbers.

## Expected results (reference run)

- The strict gate confirmed 216 of 192,000 null bands, at most 1.05% in any cell (C1, C2).
- The frozen default branch confirmed up to 82% of null bands (skewed continuous null, n = 2) and 58-59% of skewed-null bands at n = 5.
- The strict gate abstains (`UNATTAINABLE`) on every valid band with n <= 7 on these symmetric supports (C3).
- On the 382,678 bands where the frozen declared-support branch ran, the two gates made the same decisions with identical e-values below the frozen code's 10^6 reporting cap (C4).
- Every unsupported frozen route gets a non-confirming status, and the three positive controls are confirmed (C5).
- The frozen default configuration reproduces the 35 counts of the paper's Table 7 exactly (C6).

Sequential gate (reference run, 10,000 streams per cell):

- No bounded null cell confirmed more than 3.44% of its streams (skewed two-point null, N = 200; Wilson 95% 3.10-3.82%), and the Gaussian null at most 0.9% (S1, S2). The fixed-band gate, on the first N values of the same streams, confirmed at most 0.84%.
- No stream was confirmed before its eighth value (S3). Every fixed-band confirmation was also a sequential one, and every sequential confirmation at t is a fixed-band confirmation of the first t values (S4).
- At all 717,585 stops with valid values, the sequential e-value equals the fixed-band gate's on the same prefix (S5; worst relative difference 0.0). The 15 edge cases and 3 argument errors behave as registered (S6).
- For differences uniform on (-0.5, 1), mean 0.25, it confirmed 93% of streams within 50 values (the fixed band of 50: 91%) and every stream within 200, after a median of 30 values (90th percentile 47).

## Limitations

- **Simulation only.** Independent differences from six null and six alternative distributions; no dependence between instances, no adaptive reuse, no historical verdict re-checked.
- **The Gaussian rows break the strict gate's assumption** (unbounded support, declared as [-4, 4]). Bands that leave the support are refused; the Gaussian null passes only because its truncation is symmetric. A wrong support does not keep the guarantee in general.
- **Short bands.** On a symmetric support neither gate can confirm fewer than eight differences; the repair restores validity, not power, on the campaign default n = 5.
- **The sequential gate needs fresh instances.** Its guarantee assumes differences that selection never saw. Under the null it reads nearly the whole budget (a mean of 194-199 of 200 values), so the holdout must hold N fresh instances.
- **`frozen_rule.py` is a re-implementation.** It matches the audited code's decision and branch label on every band of this protocol, and on further random bands in a test that needs the audited code (see `PROVENANCE.md`). That is evidence, not a proof, for other inputs. It is meant for a level from 1e-9 to below 1 and a support given as a pair of numbers; outside these limits the two can differ. It omits report-only statistics that never enter the decision.
- **The gate files are the kit's editions, not the evaluated files.** The gates' results equal the evaluated files' on every input tried (`PROVENANCE.md` lists them), to the last bit on the author's machine; two helper functions differ on invalid arguments. On another platform the math library may round a logarithm differently in the last place; `evaluated_values.py` therefore accepts a relative difference of 1e-12 in an e-value and reports how many are bit-identical, while the two comparison scripts compare statuses, counts and the edge cases' e-values exactly.
- **Not deployed.** The strict and sequential gates are standalone functions that no live path calls.

## Citing

Christian Lysenstøen. *When the Verifier Becomes the Objective: A Verification Envelope for Self-Evolving
Research Agents.* NeurIPS 2026 Workshop "Who Verifies the Agents? Toward Reliable Agent Development".
OpenReview: https://openreview.net/forum?id=7GTg54Vm6Z
