# Provenance of the audit kit

Everything below can be checked against `SHA256SUMS.txt` (every file except that list itself). The audited
and evaluated files are identified as the paper identifies them (Appendices D, G and H): by commit and SHA-256.

## Where each file comes from

| File | Origin | Identity |
|---|---|---|
| `strict_mean_gate.py` | **The kit's edition of the strict gate.** The file evaluated for the paper (the author's branch `paper236/gate-contract-2026-11-15`, commit `a7c75dd4`, 15 Nov 2026, 20:48:49 +01:00) is not included, because its betting-fraction function was taken from the audited system. Here the constants, the fractions, the e-value loop and the capacity formula are written anew (`PlugInBets`, `betting_fractions`, `_on_unit_scale`, `max_evalue`, `evalue`), a floor of 1e-12 under the fraction's denominator, which could not bind, is left out, and the module docstring is revised. The validation helpers and the decision function `strict_mean_gate` are unchanged; 134 of the evaluated file's 182 lines remain. | see `SHA256SUMS.txt`; contract `paper236-strict-gate-1.0`. The evaluated file: sha256 `37240b412c46f65913efca0a0cd254c40cc5c271ac365130b37dd9160911133a` |
| `sequential_mean_gate.py` | **The kit's edition of the sequential gate.** The evaluated file (same branch, commit `f8177d84`, 21:53:27) is not included, for the same reason. The constants, `PlugInBets`, `_on_unit_scale`, `max_evalue` and the fraction arithmetic in its reading loop are written anew, as in the strict gate. Validation and statuses are unchanged and the messages read the same; 105 of the evaluated file's 138 lines remain. | see `SHA256SUMS.txt`; contract `paper236-sequential-gate-1.0`. The evaluated file: sha256 `e51fa3944e5b551f1e08a399aa6a9ec8e21b08fb6917730cea7110444eefcbbc` |
| `evaluated_values.py`, `reference_results/evaluated_gate_values.json` | Written for this kit. The JSON file holds what the two evaluated gate files returned on 4,000 seeded bands, recorded on 16 Nov 2026 with `evaluated_values.py --record`. The script checks the kit's editions against it. | the JSON file records the evaluated files' hashes |
| `protocol.json` | The pre-registered protocol: `docs/paper236/protocol.json`, committed with the contract in `390443b8` (20:46:49), before the gate's code and before any run. Byte-identical; `amendments` is empty. | sha256 `fd1f05b7dc3aadd2954c5101db55f07d0bdb50b47cf2d5de55baf30062209876` |
| `protocol_sequential.json` | The pre-registered sequential comparison: `docs/paper236/protocol_sequential.json`, committed with the sequential contract in `e9d87e7b` (21:51:49), before the sequential gate's code and before any run. Byte-identical; `amendments` is empty. It names the fixed-band gate by the evaluated file's hash. | sha256 `c2f92870aa39a3a63b401d6175bd8abee85eaf58f4da864eb265b163d56710ee` |
| `run_sequential.py`, `summarize_sequential.py` | Byte-identical to `docs/paper236/eval/run_sequential.py` and `docs/paper236/eval/summarize_sequential.py`, commit `37aa08f5` (21:54:53), which produced the reference run. Before that commit, a dry run on the first 100 streams of each distribution checked the plumbing, after the protocol was fixed; its outputs were not kept. | sha256 `593fa6c4…` and `b2b96449…` |
| `summarize.py` | Byte-identical to `docs/paper236/eval/summarize.py` (commit `2e5f21bb`), which produced the reference summary. | sha256 `5dd1d2bc…` |
| `make_paper_assets.py`, `make_sequential_table.py` | Byte-identical to `docs/paper236/eval/make_paper_assets.py` and `docs/paper236/eval/make_sequential_table.py`, commit `d823bbd5` (15 Nov 2026, 22:42:49 +01:00). That commit changed the first to round exact ties half up (it had used float formatting, which rounded some ties down) and added the second; regenerated from the unchanged summaries, Table 10 changed in 16 cells by +0.001, and Table 11 in two. Run on the clean-run copy's own results, both reproduce the paper's rows and Figure 2's coordinates byte for byte, and the quoted numbers with identical content. | sha256 `c10e1235…` and `b104ae3e…` |
| `frozen_rule.py` | **Written for this kit** (16 Nov 2026) from the paper's Appendix E, with an AI coding assistant under the paper author's direction, in a session that had read the audited code. Where Appendix E is silent it does what that code does (*Points taken from the audited code* below). Inside the limits stated there it returns the audited gate's decision and branch label (audit state `0cd5df96`). The audited files are not included. See also *Statement comparison*. | see `SHA256SUMS.txt` |
| `run_protocol.py`, `compare_to_reference.py` | Written for this kit. They are adapted from the authors' harness `docs/paper236/eval/run_comparison.py`, which called the audited code; the output format is the same. | see `SHA256SUMS.txt` |
| `compare_sequential.py` | Written for this kit. | see `SHA256SUMS.txt` |
| `tests/test_kit.py` | Written for this kit: 17 tests. | see `SHA256SUMS.txt` |
| `reference_results/` (except the Table 7 file and `evaluated_gate_values.json`) | The authors' single pre-registered run against the **audited** files: the gate module (sha256 `8c5cdd77…`) and its statistics module (sha256 `1ba96ebc…`), both unchanged from 9 Aug 2026 to the audit state. Two report-only functions, a bootstrap interval and a permutation p-value, were replaced by constants for speed, as registered in `protocol.json`; `run_meta.json` records 12 probe cells whose decisions were identical with and without the replacement. The strict gate in that run was the evaluated file. The run started 2026-11-15 20:51:41 +01:00 with the worktree at `2e5f21bb` and took 332.9 s. It was committed in `d64a6d69`, whose message names the wrong HEAD (`93c162a6`); the branch's `results/README.md`, commit `f0df7a58`, corrects it. | `run_meta.json` records the hashes |
| `reference_results/sequential/` | The authors' single pre-registered run of `protocol_sequential.json` with the two evaluated gate files: started 2026-11-15 21:55:02 +01:00 with the worktree at `37aa08f5`, 112.2 s, committed in `8dbddd3b` (21:58:27). No amendments. | `run_meta_sequential.json` records the hashes of both protocols and both evaluated gates |
| `reference_results/table7_calibration_results.json` | The post-acceptance replay behind the paper's Table 7 (audited gate files as above, run from commit `47c0e8da`). Its seeds are simulation seeds, not holdout seeds. | sha256 `152a7e40…` |

## Evidence that the kit's gates behave as the evaluated gates

The evaluated gate files are not in the kit. Their behavior is represented by values they returned:

- **`evaluated_values.py`** (anyone can run it). 4,000 seeded bands on seven supports, at four levels and twelve band
  sizes; some bands leave their support. Under both gates, every status and every number of values read equals what
  the evaluated files returned, and so do all 9,731 e-values and capacities. On the author's machine they are
  identical to the last bit.
- **The two protocols** (anyone can run them). The reference runs used the evaluated files.
  - `compare_to_reference.py` requires the strict gate's status on each of the 384,000 bands, the e-value agreement
    record of criterion C4 and the e-value of every edge case to equal the reference run's.
  - `compare_sequential.py` requires, for every stream, the status and the number of values read under the sequential
    gate and the status under the fixed-band gate to equal the reference run's, as well as the S4 and S5 counts and
    the 15 edge cases with their e-values.
- **A differential test that needs the evaluated files** (not reproducible from the kit). On 16 Nov 2026 every public
  function of the kit's editions and of the evaluated files was called with the same inputs: random bands, and
  malformed ones (non-numbers, missing and non-finite values, malformed supports, levels and budgets). Results were
  compared bit for bit, and exceptions by type.

| Function | Cases | Different |
|---|---|---|
| `betting_fractions` | 120,004 | 0 |
| `evalue` | 120,000 | 0 |
| `max_evalue` (both files) | 36,000 | 0 |
| `strict_mean_gate` (the whole result) | 180,000 | 0 |
| `sequential_mean_gate` (the whole result and the values read) | 180,000 | 0 |

The rewritten code performs the same floating-point operations in the same order, with two differences that cannot
change a result: the position of zero on the unit scale is written `-a / (b - a)`, where the evaluated files had
`(0.0 - a) / (b - a)`; and the evaluated files' floor of 1e-12 under the fraction's denominator is left out, because
that denominator is at least 0.17 for any data.

An independent review probed further inputs of its own on the previous commit of this version (240,000 calls of the
two gate functions, 80,000 of `max_evalue`): no difference. For the two helper functions it found differences on **invalid** arguments only:
`betting_fractions` now accepts any iterable where the evaluated function needed a sequence, and when two arguments
are invalid at once `betting_fractions` and `evalue` can raise a different error, because the level is read before
the data. All of this is evidence on the inputs tried, **not a proof** for other inputs.

## Evidence that `frozen_rule.py` reproduces the audited decision

- **The protocol** (anyone can run it). `PASSED` from `compare_to_reference.py` means three things:
  - Every band's outcome under each of the four gate configurations matches the reference run, which used the audited
    code.
  - So do the branch-label counts, the all-positive counts and the e-value equivalence counts.
  - The 20 edge cases match.
- **A differential test against the audited gate itself** (not reproducible from the kit). On 16 Nov 2026 the rule file
  and the audited gate were called on the same 90,000 bands of 0 to 40 values: Gaussian, uniform, skewed, constant,
  all-positive and two-valued bands, and bands holding a non-finite or extreme value. Each came with no support or one
  of 15 declared supports (usable, violated or malformed), at level 0.05, 0.01, 0.1 or 0.2, with the minimum off,
  `auto`, or a number (0, 1, 3, 5, 7 or 8). Decision, branch label and declared-support e-value were identical in
  every case. The audited gate's two report-only functions were replaced by constants, as in the reference run.

This is evidence of equivalence on the protocol's 384,000 bands and 20 edge cases and on those random bands, **not a
proof** for other inputs.

### Points taken from the audited code, and the limits of the comparison

Appendix E does not settle the following points. The rule file takes them from the audited code:
- a grid mean at either end of [0, 1] is moved in by 1e-9 before its bet ceilings are computed;
- for a declared support that does not straddle zero, the e-value is 1 when zero is at or above its top, and zero is
  placed at 1e-6 on the unit scale when it is at or below its bottom;
- values outside a declared support are moved to its nearer end before the e-value is computed, and a support of no
  width gives 1;
- the band size derived from the level is at least 2, and a level below 1e-9 counts as 1e-9 there;
- a minimum band size of 1 means "auto";
- the level reaches the default branch as `1 - (1 - alpha)` in floating point;
- no e-value above 10^6 is reported, and non-finite values are not rejected.

**Limits.** The rule file is meant for a level from 1e-9 to below 1, a support given as a pair of numbers, and a
minimum of None, "auto" or a whole number. Outside these limits the two can differ. In a probe of 11,520 such
cases, they agreed for levels down to 1e-12 and up to 2, for a support of three numbers or of two strings (both
raise), and for integer bounds beyond 2^53. They differed, in the result or in the type of the error, for a support
given as a dict, a string, or fewer than two entries, and for a level of 1e-17, zero or below. An independent review
found the first two limits before they were stated here; the clamp of the level and the reading of 1 were added after
it.

## The clean-directory run

The kit was copied alone into a fresh directory, with no other repository on the path, and every documented command
was run with CPython 3.14.2 (Windows 11, `-I -S`: isolated, no site-packages) on 2026-11-16, from 10:05 to
10:08 (+01:00). Every command exited with code 0. `README.md`, this file and `SHA256SUMS.txt` were completed
after that run; every other file is the one that ran. The tests, `evaluated_values.py` and the two quick checks were
also run on the same files with CPython 3.12.10: the same results, with all 9,731 values identical to the
last bit. An independent review had reproduced every command on the previous commit of this version, with both
interpreters.

| Step | Result |
|---|---|
| `python -I -S -m unittest discover -s tests` | 17 tests, OK |
| `python -I -S evaluated_values.py` | `e-values and capacities compared: 9731; identical to the last bit: 9731` / **PASSED** |
| `python -I -S run_protocol.py` | 120 cells in 72.9 s |
| `python -I -S compare_to_reference.py` | `compared 120 cells (384000 bands x 4 gates) and 20 edge cases` / **PASSED** |
| `python -I -S summarize.py --protocol protocol.json --raw results --table7 reference_results/table7_calibration_results.json` | C1-C6 all true |
| `run_sequential.py ... --streams 500`, then `compare_sequential.py --results results_sequential_quick` | `compared 72 of 72 cells (0 full, 36000 streams x 2 gates), 15 edge cases and 3 argument errors` / **PASSED** |
| `run_sequential.py ...` (full protocol, 98 s), then `python -I -S compare_sequential.py` | `compared 72 of 72 cells (72 full, 720000 streams x 2 gates), 15 edge cases and 3 argument errors` / **PASSED** |
| `summarize_sequential.py ...` | S1-S6 all PASS |
| `make_paper_assets.py`, `make_sequential_table.py` | exit 0; the generated rows of Tables 10 and 11 and Figure 2's coordinates are the paper's |

## History

- **15 Nov 2026.** The kit was assembled for the author's own checks. Its rule file was a condensed transcription of
  the audited functions.
- **16 Nov 2026, 05:41 to 06:35 (+01:00).** That version was public for 54 minutes in another repository, as
  v1.0.0, and was withdrawn: an independent review found that most of the rule file's lines were the audited
  functions' own.
- **16 Nov 2026, second version (never published).** The rule file was rewritten. A second review found that the two
  gate files, kept byte-identical to the evaluated ones, held a function of the audited statistics module, and that
  two helper functions of the rewritten rule file still followed the audited ones statement by statement.
- **16 Nov 2026, this version (v1.1.0).** The fraction arithmetic of both gates was written anew and the rule file
  was restructured: `capital_path`, `bet_ceiling`, `excluded`, `support_holds`, `minimum_band`, `on_unit_scale` and
  `zero_on_unit_scale` are new, `required_n`, `declared_support_evalue`, `observed_range_lower_end` and `frozen_gate`
  were rewritten, and `plug_in_fractions` is largely the second version's (which was this kit's own text). The
  evidence above was added. `run_protocol.py` follows the rule file's new result keys; `compare_sequential.py` reports
  the gates' hashes, which no longer equal the reference run's; `tests/test_kit.py` gained two tests of the fractions
  against the formula printed in Appendix E.
- **16 Nov 2026, a third independent review, of this version.** It found no statement, function or longer run of the
  audited modules in the kit, and the smaller things listed under *Statement comparison*. After it, `required_n` was
  rewritten with the audited clamp, a parameter name and the 1e-12 floor were removed from the gates, the limits of
  the rule file were stated, and several sentences of these notes were corrected.

## Statement comparison with the audited modules

Each Python file here was parsed, and every statement was compared with every statement of the three audited
statistical modules (the confirmation gate, its statistics module and the campaign module; 684 statements, `try` lines aside)
as a syntax tree, at three levels: identical; identical after local names are replaced by placeholders; identical
after every name and attribute is replaced. For a compound statement (`for`, `if`, `def`) the header is compared.
Statements of fewer than six expression nodes, such as `return 1.0` or `import math`, are counted apart, because they
recur in any Python code.

- `frozen_rule.py`, `strict_mean_gate.py` and `sequential_mean_gate.py` (131, 128 and 109 statements):
  no statement of six nodes or more coincides with an audited statement, at any of the three levels.
- The other files: six loop headers coincide after renaming, of the forms `for k, v in x.items():` and
  `for a, b in zip(c, d):`. Nothing else coincides.
- No function of the kit has two consecutive statements that are also consecutive in an audited function, once a
  statement of six nodes or more is among them.
- Small statements that also occur in the audited modules: 94 in the whole kit. They are imports, bare
  returns of a constant or a name, `continue`, simple tests such as `if n == 0:` or `if __name__ == '__main__':`,
  and the assignments `out = []` and `rng = random.Random(seed)`.

By the cruder measure used for the earlier versions (verbatim code lines of at least 16 characters):
each of the three rewritten files shares two such lines with the audited modules (`from __future__ import annotations`, and `import statistics` or `if support is None:`), and no file of the kit shares more than three, all of that kind.

An independent review used other measures (runs of tokens after renaming, expression subtrees, word sequences). It
confirmed that no statement, function or longer run of the audited modules is in the kit, and it found smaller
things:
- **Changed after it:** one return statement of the rule file that repeated the audited line apart from a wrapper;
  the parameter name `xs01` and the 1e-12 floor in the two gates; two consecutive short statements of
  `declared_support_evalue`.
- **Remaining, and needed:** the constants with which the rule agrees with the audited gate (240, 0.5, 1e-9, 1e6,
  0.05, 1e-6), the terms of the printed formula, and common idioms such as
  `all(low <= value <= high for value in band)` and `len(set(band)) < 2`.
- **Remaining, in structure:** `declared_support_evalue` and `observed_range_lower_end` perform the same steps in the
  same order as the audited functions they reproduce, each step in other words. The order is largely fixed by the
  data flow.

What this comparison cannot show: the three files implement the formulas of the paper's Appendices E and H, as the
audited code does, so the same arithmetic appears here in other words; and they were written in a session that had
read the audited code.

## What is deliberately absent

- The audited system's source files, and the two gate files as evaluated, which held a function of it.
- Named but not included: `protocol.json`, `protocol_sequential.json` and the reference results are kept
  byte-identical, because they are records. They name three files, three functions, one argument, two result keys and
  one environment setting of the audited system, carry its ten branch labels, and give the gate files' location
  in the author's repository. `frozen_rule.py` emits the same branch labels, so that runs can be compared. Criterion
  C5 of `protocol.json` cites a contract document of that repository which is not in the kit; `summarize.py` holds
  the list of cases it refers to. `run_sequential.py` and this file give paths of the author's repository
  (`docs/paper236/...`).
- Orchestration, prompts and research policy.
- Live holdout instances, holdout seeds and seed-to-instance maps.
- Credentials and correspondence.
- Machine paths: the reference results were scanned for local paths and names, and none were found. Four of them
  record the platform string of the author's machine and its Python version.

## Release v1.1.0 (16 Nov 2026)

Against the second version (see *History*), this version changed `strict_mean_gate.py`, `sequential_mean_gate.py`
and `frozen_rule.py` (see *History* for what was rewritten), `run_protocol.py`, `compare_to_reference.py` (two
docstring lines), `compare_sequential.py`, `tests/test_kit.py`, `.github/workflows/reproduce.yml` (one step added; the
workflow has not run), `README.md` and this file. It added `evaluated_values.py` and
`reference_results/evaluated_gate_values.json`. `SHA256SUMS.txt` was regenerated. Both protocols, the summarizers,
the table generators and `run_sequential.py` are byte-identical to the versions named above.

Line endings of the reference results: `edge_cases.json`, `run_meta.json`, `summary.json` and the Table 7 file carry
CRLF, as written on Windows; the author's repository stores the first three with LF. The files under
`reference_results/sequential/` are the copies committed in the author's repository, with LF. The content is the same
either way. `.gitattributes` turns off end-of-line conversion, so that a clone matches the checksums.

## How the kit was made

Its files were written and checked in AI-assisted sessions (Claude), under the paper author's direction, as the
paper's Appendix G says of the post-acceptance work. The commit's trailer records the same.
