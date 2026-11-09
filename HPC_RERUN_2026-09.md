# HPC rerun — September 2026

Stages 04, 05 and 06 must be rerun. This file is the operational handoff: what changed, what
to transfer, what to delete, what order to run things in, and what is stale when it
finishes.

Stage 04's *values* are valid — it is a transductive reconstruction experiment and the defect
never touched it. It is rerun because its **schedule** changed: on pure-continuous data 9 of
its 21 labels compute nothing new, and rerunning is cleaner than deriving a de-duplicated CSV
from the old one. It is ~4-7h of cluster time and removes a whole class of provenance
bookkeeping. Stage 04 keeps SoftImpute and SoftImpute+Mode; only stages 05 and 06 drop them.

The plan this implements is archived at `archive/plans/PLAN_stage05_inductive_fix_v4.md`.

---

## 1. Why

`shared/runners.py:_impute_one_method_stage05()` called `apply_imputation_mixed_types()`
twice — once on the training half, once on the test half. That function is `fit_transform`,
so the test matrix fitted a **second** imputer and the train-fitted one was discarded. Every
"out-of-sample" number in stages 05 and 06 was a second in-sample number.

Confirmed bit-for-bit on `dataset_006_rep01` / block / pure-continuous / MCAR / 10% / Mean,
regenerated from seeds alone (`split_seed=11043`, `train_seed=6011`, `test_seed=13930`) and
scored on the 1,927 deleted test cells:

| Evaluation | Test RMSE |
|---|---:|
| Saved in `imputation_results.csv` | `2.281571182876898` |
| Fit on **test** → transform test | `2.281571182876898` |
| Fit on **train** → transform test | `2.2795752629683292` |

### What is and is not affected

| Artifact | Status |
|---|---|
| Stage 05 test-recovery metrics | **Invalid** |
| Stage 05 imputed **training** files | **Valid** — the train fit was always real |
| Stage 06 `Complete`, `Missing`, `GT_*`, `CV_*` | **Valid** — they derive from valid training completions |
| Stage 06 `Internal_*`, `Delta_*` | **Invalid** |
| Stage 04 (all values) | **Valid** — transductive by design. Rerun only because its schedule shrank, not because any number was wrong |
| Knowledge DB out-of-sample recommendations, all 05/06 figures and stats, both decks | **Provisional** until corrected 05 and 06 are ingested |

Preserving the training completion exactly is what turns `GT_F1` / `CV_Mean_F1` bit-identity
into a free regression check on the whole rerun (§7).

### Three further changes ride along

1. **Alias de-duplication.** On pure-continuous data the `+Mode` and `-all` suffixes do
   nothing, so 9 labels named computations already in the file. Eight pairs were exactly
   identical; SoftImpute's agreed to `3.2e-12`. Stage 04 now schedules 12 methods there
   instead of 21 (87,750 → 75,600 rows); stages 05 and 06 never generate them at all.
2. **Incomplete pipelines dropped from 05/06.** `Mean` on mixed data fills only the
   continuous columns and leaves the discrete ones for XGBoost's native NaN handling to
   fill — then the row is labeled `Mean`. That credits `Mean` with a capable method it did
   not supply. Those 7 standalone configurations are no longer generated on mixed data. No
   component evidence is lost: `Mean+Mode` runs the same `SimpleImputer` on the same
   columns, and the per-feature-type rows carry both labels.
3. **SoftImpute is stage 04 only.** `fancyimpute 0.7.0` exposes no inductive transform and
   discards the factorization; the R `softImpute` package imputes only fitted rows. Any
   new-row procedure would be project-local mathematics nobody could replicate, so none was
   written. The limitation is disclosed per query as `excluded_candidates` with reason
   `not_inductive`, not hidden.

---

## 2. Transfer list

Generated from the files actually changed, not from a generic list. Everything below is
under `Version2/`.

The repair itself is small — it lives in `shared/imputation.py`, `shared/runners.py` and
`shared/method_catalog.py`. The file count comes from the four other items bundled into this
rerun: the test suite that proves the fix (4 files), the dataset profiler and the knowledge
DB v2 split (3 modules), and the two validation gates.

### New files (9)

```
shared/recommendation.py                      profile_dataset + query_recommendation
shared/profiling.py                           the registry's correlation statistics
shared/_env.py                                environment + scikit-posthocs assertion
02_eda_and_registry/validate_profiler.py      profiler validation over all 270 datasets
05_train_test_imputation/validate_stage05.py  the inductive validation gate
tests/conftest.py
tests/fixtures.py
tests/test_inductive_imputation.py
tests/test_knowledge_db_v2.py
```

### Changed code (12)

```
shared/imputation.py                              fit_transform_train + FittedImputer
shared/method_catalog.py                          methods_for_stage + alias_map + 3 new fields
shared/runners.py                                 inductive stage-05 loop, build_prediction_effects,
                                                  stage-04 schedule filter + expected_rows_stage04
shared/knowledge_db.py                            schema 2.0; profiler-gate fallback removed
shared/figures.py                                 Internal_F1 default, per-mix figS1, holdout_label
shared/stats.py                                   scikit-posthocs version assertion
04_imputation_eval/run_impute_eval.py              --run-id + aggregator guard
05_train_test_imputation/run_train_test_imputation.py
06_predictive_analysis/run_predictive_analysis.py
06_predictive_analysis/run_prediction_figures.py  --holdout {operational,clean_test}
07_knowledge_db/run_knowledge_db.py
07_knowledge_db/verify_knowledge_db.py
```

### Changed dependency files (2)

```
environment.yml      scikit-posthocs=0.11.2 (unchanged pin, now enforced at runtime)
requirements.txt     scikit-posthocs==0.11.2
```

### Changed documentation (14)

Not needed to run anything. Transfer them so the cluster copy does not describe a pipeline
that no longer exists.

```
CLAUDE.md   README.md   Methods.md   FIGURES.md   shared/README.md
01_data_simulation/README.md    02_eda_and_registry/README.md
04_imputation_eval/README.md    05_train_test_imputation/README.md
06_predictive_analysis/README.md   07_knowledge_db/README.md
results/README.md   results/knowledge_db/README.md
HPC_RERUN_2026-09.md
```

The last one is this file. Optional: nothing reads it. Without it the cluster copy of the
repo carries no record of why stages 04–06 were rerun.

### Deliberately NOT transferred

- **Both `submit.sh` files are unchanged.** The new `--run-id` flag defaults to
  `$SLURM_ARRAY_JOB_ID`, which every task of an array already shares, so the submission
  scripts need no edit. Do not overwrite them.
- All notebooks, `shared/missingness.py`, `shared/prediction.py`, `shared/_threads.py`, and
  every stage 01/02/03 driver. None changed.
- `presentation/` — rebuilt at the very end, after the corrected numbers exist (§9).

Suggested transfer, from the laptop:

```bash
cd ".../DataCleaning/Version2"
rsync -av --relative \
  shared/recommendation.py shared/profiling.py shared/_env.py \
  shared/imputation.py shared/method_catalog.py shared/runners.py \
  shared/knowledge_db.py shared/figures.py shared/stats.py shared/README.md \
  02_eda_and_registry/validate_profiler.py \
  05_train_test_imputation/validate_stage05.py \
  05_train_test_imputation/run_train_test_imputation.py \
  06_predictive_analysis/run_predictive_analysis.py \
  06_predictive_analysis/run_prediction_figures.py \
  07_knowledge_db/run_knowledge_db.py 07_knowledge_db/verify_knowledge_db.py \
  04_imputation_eval/run_impute_eval.py \
  tests/ \
  environment.yml requirements.txt \
  CLAUDE.md README.md Methods.md FIGURES.md \
  01_data_simulation/README.md 02_eda_and_registry/README.md \
  04_imputation_eval/README.md 05_train_test_imputation/README.md \
  06_predictive_analysis/README.md 07_knowledge_db/README.md \
  results/README.md results/knowledge_db/README.md \
  HPC_RERUN_2026-09.md \
  <user>@<cluster>:<project>/Version2/
```

Two `results/*.md` paths are in that list on purpose: they are documentation that happens to
live under `results/`, and `--relative` places them correctly. That is the only thing under
`results/` you should ever push.

**Do not rsync `results/` in either direction after this point.** The laptop copy of
`results/` is the superseded run, and pushing it would recreate exactly what §3 deletes.

---

## 3. Delete the old runs — what and why

**The commands are step 4 of the runbook (§5).** This section is the rationale.

Mandatory, not advisory. Both aggregators used to glob `checkpoints/*.csv` and concatenate,
so leaving old task CSVs in place would silently mix corrected and defective rows. The new
aggregators refuse a directory holding more than one `run_id` or `schema_version`, but the
old outputs still have to go so the corrected ones can take their paths.

The stage 05 and 06 outputs on the cluster are invalid and are not needed. Stage 04's
checkpoints go too: its schedule changed, so a 1.x checkpoint carries 21 labels per
pure-continuous scenario where the new one carries 12, and the aggregator will refuse to mix
them.

**Three CSVs are copied out first and must survive.** `prediction_results.csv`,
`imputation_results.csv` and `ImputeEval_Results_Detailed.csv` are the comparison side of the
two regression gates (steps 6 and 10), which assert the new `GT_F1`, `CV_Mean_F1` and every
retained stage-04 value are bit-identical to the old ones. The gates cannot run without them.
All three are cluster-computed, which is what makes the comparison valid (§6). Together they
are about 100 MB. After both gates pass they can go too.

### What is being deleted

| Path | Contents | Why it can go |
|---|---|---|
| `train_test_imputation/` | `imputation_results.csv`, `checkpoints/*.csv`, the per-dataset tree `{dataset_id}/{MECH}_{rate}pct/{method}_{train,test}.csv` plus `ground_truth_*.csv` and `missing_*.csv`, 8 figures, `stats/` | Test-side values invalid; regenerated in full by step 7 |
| `predictive_analysis/` | `prediction_results.csv`, `checkpoints/*.csv`, `method_ranking_honest.csv`, 11 figures, `by_metric/`, `internal_f1_deployment/`, `stats/` | `Internal_*` and `Delta_*` invalid; regenerated by step 9 |
| `knowledge_db/*.json`, `*.db` | the v1.2 stores | Schema 2.0 is a MAJOR bump; a 1.x file raises on load and must be rebuilt anyway |
| `impute_eval/checkpoints/` | 270 stage 04 task CSVs | Schema 1.x: 21 labels per pure-continuous scenario vs 12 now. The results CSV is kept as a reference |

The imputed training CSVs under `train_test_imputation/` were always valid, and deleting
them is still correct: step 7 regenerates them bit-for-bit from the same seeds, which is
what step 10's `GT_F1` identity check proves.

Two items go with the rest and are **not** regenerated:

- `figS1_discrete_subset_effects.png` is a retired figure name. The supplementary is now one
  figure per feature mix, `figS1_effects_<mix>.png`.
- `internal_f1_deployment/` was produced by three scripts in `presentation/archive/v3_build/`,
  not by the pipeline. The decomposition it computed is now
  `shared/figures.py:save_pipeline_decomposition()`, recomputed from the corrected run and
  never copied forward.

---

## 4. Environment notes

`scikit-posthocs` must resolve to **0.11.2**. That is the version the published CD diagrams
came from, and step 12 regenerates those diagrams. A mismatched install now fails loudly in
the stats path instead of quietly producing different Nemenyi results.

The commands are step 1 of the runbook below.

---

## 5. The runbook — run these in order

Everything runs on the cluster, from `<project>/Version2`. Every command is here; you should
not have to jump to another section to run anything. Each step's gate must pass before the
next starts. Steps 5, 7 and 9 are the three array jobs; everything else is seconds to
minutes.

| Step | What | Time |
|---:|---|---|
| 1–3 | Environment, tests, profiler validation | ~10 min |
| 4 | Delete the old runs | seconds |
| 5–6 | Stage 04 + its regression gate | ~4–7 h |
| 7–8 | Stage 05 + its validation gate | hours |
| 9–10 | Stage 06 + the 05/06 regression gate | the long pole |
| 11–13 | Knowledge DB, figures, decks | ~1 h |

```bash
cd <project>/Version2
RUN_ID="2026-09-inductive"
```

Keep that shell open, or re-export `RUN_ID` in every new one. Steps 7 and 9 stamp it into
the results, and the aggregators refuse checkpoints carrying more than one value.

---

### Step 1 — Environment

```bash
conda env update -f environment.yml --prune     # or: pip install -r requirements.txt
python -c "import shared._env as e; e.assert_stats_environment()"
```

Check the cluster environment against `environment.yml` while you are here. If numpy, scipy
or scikit-learn moved since July, MICE-Linear will drift for reasons unrelated to this repair
and step 6 will flag it — see §6.

### Step 2 — Tests and import weight

```bash
pytest tests/ -q                                # 195 tests, all of them
python 07_knowledge_db/verify_knowledge_db.py   # must print: ALL CHECKS PASSED
```

No test reads `data/` or the real registry; they run on small fixtures.
`verify_knowledge_db.py` also asserts the import-weight contract: `shared/profiling.py`
imports numpy/pandas/scipy only, and `shared/knowledge_db.py` / `shared/recommendation.py`
import only pandas/numpy plus `method_catalog`, so the DB stays rebuildable on a laptop.

### Step 3 — Profiler validation

Minutes, one core. Needs `data/` and the registry, nothing else, so it runs before the arrays.

```bash
python 02_eda_and_registry/validate_profiler.py
# -> results/registry/profiler_validation.json
```

Thresholds A–F are module-level constants in that script, fixed before its first run. A
missing, stale or failing report sets `correlation_match_unreliable` in the knowledge DB,
down-weights correlation in regime matching, and stamps the warning on every response.

**Regenerate it here even though a local copy exists.** The laptop run passed all six
thresholds (sha256 `1af0a6bd0ba2…c1c931f21e1c45847`, 2 errors, both `medium` predicted as
`block`), but it describes the laptop's package versions. The report's hash goes into the
DB's slot provenance, so it must describe the environment the rerun actually used.

### Step 4 — Delete the old runs

Mandatory. The old stage 05 and 06 outputs are invalid and their checkpoints would be
rejected anyway; they have to go so the corrected ones can take their paths. Three CSVs are
copied out first — they are the comparison side of steps 6 and 10, and those gates cannot run
without them. §3 explains what each deletion covers.

```bash
KEEP="results/prerun_reference/${RUN_ID}"
test -e "$KEEP" && { echo "REFUSING: $KEEP already exists"; exit 1; }
mkdir -p "$KEEP"

# The three regression-gate references, copied out before anything is removed.
cp results/predictive_analysis/prediction_results.csv      "$KEEP"/prediction_results.csv
cp results/train_test_imputation/imputation_results.csv    "$KEEP"/imputation_results.csv
cp results/impute_eval/ImputeEval_Results_Detailed.csv     "$KEEP"/ImputeEval_Results_Detailed.csv
for f in "$KEEP"/*.csv; do test -s "$f" || { echo "REFUSING: $f copy failed"; exit 1; }; done
shasum -a 256 "$KEEP"/*.csv > "$KEEP"/SHA256SUMS

# Now the invalid runs.
rm -rf results/train_test_imputation
rm -rf results/predictive_analysis
rm -rf results/impute_eval/checkpoints
rm -f  results/knowledge_db/imputation_knowledge.json
rm -f  results/knowledge_db/imputation_knowledge.db

mkdir -p results/train_test_imputation results/predictive_analysis results/impute_eval
echo "kept references in $KEEP; old stage 05/06 runs deleted"
```

### Step 5 — Stage 04

270 array tasks, `--time=04:00:00`, ~4–7 h wall clock at 50 concurrent. `submit.sh` is
unchanged — do not edit it.

```bash
sbatch 04_imputation_eval/submit.sh
# wait for all 270 tasks to finish, then:
python 04_imputation_eval/run_impute_eval.py --aggregate
wc -l results/impute_eval/ImputeEval_Results_Detailed.csv    # -> 75,601 (75,600 + header)
```

```
 90 × 15 × 12 = 16,200   pure_continuous  (was 21 methods, now 12)
180 × 15 × 22 = 59,400   mixed + binary_heavy  (unchanged)
                75,600   (from 87,750, −12,150)
```

Neither command takes a run ID. Inside an array task `default_run_id()` returns
`$SLURM_ARRAY_JOB_ID`, which all 270 tasks of one submission already share and which
outranks the `IMPUTE_EVAL_RUN_ID` fallback, so `--export` would be ignored. `--aggregate`
reads that ID off the checkpoints rather than taking a flag. The stage-04 `run_id` will
therefore be a numeric SLURM job ID, not `$RUN_ID`; the aggregator only requires internal
consistency. Write the job ID down next to `$KEEP` so the CSV and its reference stay
associated.

Both SoftImpute entries still run here. The schedule restriction happens inside
`evaluate_stage04`, which reads the dataset's own feature types, so the driver cannot widen
it.

### Step 6 — Stage 04 regression gate

Seconds. **Run this before launching stage 05.** Stage 04 is rerun under a narrower schedule,
not a changed method, so every retained row must reproduce its pre-rerun value exactly. It is
the only step where the right answer is known in advance, which makes it the cleanest test of
whether the cluster environment moved since July.

Save the block below as `gate_stage04.py` and run `python gate_stage04.py`.

```python
import pandas as pd
old = pd.read_csv('results/prerun_reference/2026-09-inductive/ImputeEval_Results_Detailed.csv')
new = pd.read_csv('results/impute_eval/ImputeEval_Results_Detailed.csv')
key = ['Dataset_ID', 'Mechanism', 'Missingness_Rate_Pct', 'Method']
print('old rows', len(old), '-> new rows', len(new))     # 87,750 -> 75,600
m = old.merge(new, on=key, suffixes=('_old', '_new'))
print('joined', len(m))                                   # must equal 75,600
metrics = [c for c in ('RMSE_continuous', 'Accuracy_binary', 'F1_binary',
                       'Accuracy_categorical', 'F1_categorical')
           if f'{c}_old' in m.columns]
for col in metrics:
    d = (m[f'{col}_old'] - m[f'{col}_new']).abs()
    print(f'{col:24s} n={d.notna().sum():6d}  max abs diff = {d.max()}')
    if d.max() and d.max() > 1e-12:
        print(m.assign(_d=d).nlargest(5, '_d')[key + ['_d']].to_string(index=False))
```

**Pass:** `joined` is exactly 75,600 and `max abs diff` is `0.0` on every metric, except
possibly the two MICE-Linear entries if the environment moved (§6). Fewer joined rows means
the rerun lost work-units; more is impossible unless a duplicate key slipped past the
aggregator guard. Anything else — stop before spending 4,050 tasks on stage 06.

Timing columns will differ. They are wall clock on different hardware and are not part of
this gate.

### Step 7 — Stage 05

270 array tasks.

```bash
sbatch --export=ALL,STAGE05_RUN_ID="$RUN_ID" 05_train_test_imputation/submit.sh
# wait for all 270 tasks to finish, then:
python 05_train_test_imputation/run_train_test_imputation.py --aggregate --run-id "$RUN_ID"
wc -l results/train_test_imputation/imputation_results.csv   # -> 52,651
```

```
 90 × 15 × 11 = 14,850   pure_continuous
180 × 15 × 14 = 37,800   mixed + binary_heavy
                52,650   (from 87,750)
```

The aggregator requires one `schema_version` and one `run_id` across all checkpoints, fails
on duplicate work-unit keys, verifies method-by-feature-mix coverage rather than accepting
any glob count, and writes atomically. It derives the expected counts from
`methods_for_stage()`, so a future catalog change cannot leave a stale hard-coded number.

### Step 8 — Stage 05 validation gate

Must pass before stage 06 launches.

```bash
python 05_train_test_imputation/validate_stage05.py --n-per-cell 2
# -> results/train_test_imputation/stage05_validation.json
```

Over a stratified sample it recreates the split and missingness from saved seeds, refits on
the training frame, applies that artifact to the test frame, and asserts: the regenerated
test CSV equals the saved one; where refit-on-test differs, the saved output does **not**
equal it; the saved training CSV equals the pre-repair training completion; no target column
entered any imputer; zero residual NaN; no incomplete standalone ran on mixed data; no alias
label ran on pure-continuous data; and SoftImpute appears nowhere. The report's SHA-256 is
stored in the DB as `validation_report_sha256`.

### Step 9 — Stage 06

4,050 array tasks, the long pole. 23% smaller than the previous run.

```bash
sbatch --export=ALL,STAGE06_RUN_ID="$RUN_ID" 06_predictive_analysis/submit.sh
# wait for all 4,050 tasks to finish, then:
python 06_predictive_analysis/run_predictive_analysis.py --aggregate --run-id "$RUN_ID"
wc -l results/predictive_analysis/prediction_results.csv    # -> 60,751
wc -l results/predictive_analysis/prediction_effects.csv    # -> 52,651
```

```
Imputed:   90 × 15 × 11  +  180 × 15 × 14  =  14,850 + 37,800  =  52,650
Complete:  270 × 15                                            =   4,050
Missing:   270 × 15                                            =   4,050
                                                    raw total  =  60,750
Effects:   one joined row per imputed row                      =  52,650
```

`prediction_effects.csv` is built by joining condition rows on
`(Dataset_ID, Config_Name, Correlation, Feature_Mix, Mechanism, Missingness_Rate_Pct)`.
Each eligible Imputed row must join exactly one Complete and one Missing row; a missing or
duplicate match fails the aggregation. The aggregator asserts
`total_pipeline_effect = training_side_effect + test_time_imputation_effect` row-wise at
`atol = 1e-12`.

### Step 10 — Stage 05/06 regression gate

Because the repair preserves each method's own training completion, the training side must
not move. Run this before rebuilding anything downstream. Save as `gate_stage0506.py`.

```python
import pandas as pd
old = pd.read_csv('results/prerun_reference/2026-09-inductive/prediction_results.csv')
new = pd.read_csv('results/predictive_analysis/prediction_results.csv')
key = ['Dataset_ID', 'Mechanism', 'Missingness_Rate_Pct', 'Condition', 'Method']
m = old.merge(new, on=key, suffixes=('_old', '_new'))
for col in ('GT_F1', 'CV_Mean_F1'):
    d = (m[f'{col}_old'] - m[f'{col}_new']).abs()
    print(col, 'n=', len(d), 'max abs diff =', d.max())
    print(m.assign(_d=d).nlargest(5, '_d')[key + ['_d']].to_string(index=False))
```

**Pass:** `0.0` for every method on both `GT_F1` and `CV_Mean_F1`. If only the two
MICE-Linear entries are nonzero and the cluster environment moved since July, that is the §6
caveat, not a bug. Anything else is — stop and diff that method's old and new training CSV
before trusting anything downstream. §7 lists what else must be identical, what is expected
to change, and what is absent by design.

### Step 11 — Knowledge DB (stage 07)

```bash
python 07_knowledge_db/run_knowledge_db.py --rebuild
python 07_knowledge_db/run_knowledge_db.py --status
python 07_knowledge_db/verify_knowledge_db.py
```

`--rebuild` discards the existing DB, backfills every slot whose CSV exists, and recompiles
the recommendations — it implies `--all`, so neither `--all` nor a separate
`--recommendations` pass is needed here. Schema 2.0 is a **MAJOR** bump, so a 1.x file raises
on load and `--rebuild` is required, not optional.

This driver takes **no** `--run-id`. Each slot's run ID comes from the `run_id` column of the
CSV it reads, which is what steps 5, 7 and 9 stamped. Passing `--run-id` here fails with
`unrecognized arguments`.

`--status` prints the slot freshness table; every slot should show the expected run ID and a
current `code_fingerprint`.

Then confirm both scopes answer:

```python
from shared.knowledge_db import load_db
from shared.recommendation import profile_dataset, query_recommendation
db = load_db()
p = profile_dataset(df_train, target_col='target', db=db)
query_recommendation(db, p)                               # whole_dataset
query_recommendation(db, p, scope='per_feature_type')     # components + untested assembly
```

### Step 12 — Figures and statistics

Stages 04, 05 **and** 06.

```bash
python 04_imputation_eval/run_imputation_figures.py
python 05_train_test_imputation/run_train_test_figures.py
python 06_predictive_analysis/run_prediction_figures.py                    # operational
python 06_predictive_analysis/run_prediction_figures.py --holdout clean_test
```

Stage 04 is included even though **no stage 04 value changed**: its pure-continuous CD
diagrams and Kendall's *W* were computed over 21 competitors when there were 12. Report that
as a correction, not as a silent refresh.

### Step 13 — Presentation and manuscript

Last, and only from the validated corrected run. Both decks need **code changes before they
will build** — four of them, listed in §9. Fix those first, then:

```bash
python presentation/build_chapter_deck.py
python presentation/qa_chapter_deck.py        # must print: clean.
python presentation/build_presentation.py
```

### Optional — determinism spot-check

Not a gate, but the fastest confirmation that the corrected code is what ran. §8 has the
detail.

```bash
python 05_train_test_imputation/run_train_test_imputation.py \
    --dataset-id dataset_006_rep01 --no-miceforest --num-cpus 1
```

`dataset_006_rep01` / MCAR / 10% / Mean must give `RMSE_continuous = 2.2795752629683292`,
**not** `2.281571182876898`. That single number distinguishes the corrected code from the
defective code.

---

## 6. Two caveats that affect how you read the gates

### MICE-Linear does not reproduce across environments

A local reproduction of stage 04 from the saved inputs matched 20 of 22 methods to
`≤ ~1e-13`. **MICE-Linear (5 iter) and MICE-Linear (10 iter) did not** — up to `6.5e-3` on
`Accuracy_categorical`. The cause is `LogisticRegression(solver='lbfgs', max_iter=100)`
failing to converge inside the MICE column loop: the returned coefficients then depend on
BLAS arithmetic, so a different machine or library build lands somewhere else. The
convergence warnings are in the run log.

**Consequence for the gates.** The `GT_F1` / `CV_Mean_F1` bit-identity check in §7 is only
sound **within one environment**. Both sides of that comparison must come from the same
machine and the same package versions, or MICE-Linear will differ for reasons that have
nothing to do with this repair and you will not be able to tell machine noise from a real
bug.

Practically, that means two things:

- The reference CSV step 4 keeps was computed on the cluster in July. It stays the "old" side.
  Do not regenerate old numbers locally to compare against — a laptop-versus-cluster diff
  will show MICE-Linear drift by construction.
- **Check the cluster environment has not changed since July.** If conda was updated in the
  meantime, "old cluster env A" versus "new cluster env B" has the same problem. Compare
  `conda list` against the pins in `environment.yml`. If numpy, scipy or scikit-learn moved,
  treat MICE-Linear's two entries as expected drift and record that, rather than failing the
  gate on them — but hold every other method to bit-identity.

This is not a defect introduced here and it does not affect the repair. Two things follow
anyway. "Bit-identical" is an environment-local claim, so any writeup should say so. And
`6.5e-3` on an accuracy metric is 0.65 points, not rounding noise — MICE-Linear's reported
values carry environment-dependent uncertainty around `1e-3` that no CI in this project
currently shows. Add a sentence to `Methods.md` limitations. Raising `max_iter` would fix the
instability but would change every MICE-Linear number in the project, so it is not part of
this rerun.

### There is no git repository

`code_fingerprint` in the DB's slot provenance is a SHA-256 over a per-slot manifest of the
producing source files, not a commit hash. It is per-slot by design: hashing all of
`shared/*.py` would let an edit to `figures.py` invalidate the stage-05 slot. This is weaker
provenance than a commit and is stated rather than papered over.

---

## 7. What the two regression gates mean

**The scripts are steps 6 and 10 of the runbook (§5).** This section is how to read their
output.

### Stage 04 — every retained row must be bit-identical

Stage 04 is rerun under a narrower schedule, not a changed method. Same seeds, same twelve or
twenty-two methods, same data, so the 75,600 rows that survive must reproduce their pre-rerun
values exactly.

`joined` must equal 75,600 exactly. Fewer means the rerun lost work-units; more is impossible
unless a duplicate key slipped past the aggregator guard. **Do not** expect the dropped rows
to be missing from `old` — they are in it, which is why the join is the check: 87,750 rows
join 75,600 rows on 75,600 keys, and the 12,150 that do not join are precisely the alias
labels.

Expect `0.0` on every metric except the two MICE-Linear entries, which are the §6 caveat.
Timing columns will differ; they are wall clock on different hardware and are not part of
this gate.

### Stages 05 and 06 — the training side must not move

Because the repair preserves each method's own training completion, the training-side results
must not move.

**Must be bit-identical** to the reference CSV step 4 kept, for every Imputed condition that
still exists:

- `GT_F1` and every other `GT_*` metric
- `CV_Mean_F1`
- every `Complete` and every `Missing` row

**Expected to change:**

- `Internal_*` — the whole point of the repair
- `Delta_*` (now reported as `test_time_imputation_effect`)
- every stage 05 test-recovery metric

**Absent by design, not regressions:** all `SoftImpute` and `SoftImpute+Mode` rows in stages
05 and 06; the 7 incomplete standalone configurations on mixed and binary-heavy data; the 9
alias labels on pure-continuous data.

Expect `0.0` for every method. If only the two MICE-Linear entries are nonzero and the
cluster environment moved since July, that is the §6 caveat, not a bug. Anything else is. If
an Imputed method's `GT_F1` or CV result moves, **stop** and diff its old and new training
CSV before trusting anything downstream.

**miceforest is the one method to watch.** Its fit now uses `save_all_iterations_data=True`,
which `impute_new_data()` requires. That must not perturb the training completion. If it
does, this is **not** waivable as a documented exception — the whole rerun leans on
training-side results being historically unchanged. miceforest would instead get an
`implementation_version` bump in the catalog, and its training-side and CV results would be
recomputed and relabeled as a new implementation, including its stage 04 row, so no document
claims the old and new numbers describe the same estimator.

---

## 8. Determinism checks

Parallelism must not change a seed (CLAUDE.md §5).

```bash
# Same seeds twice, and serial vs 2 Ray workers, byte-identical
python 05_train_test_imputation/run_train_test_imputation.py \
    --dataset-id dataset_006_rep01 --no-miceforest --num-cpus 1
python 05_train_test_imputation/run_train_test_imputation.py \
    --dataset-id dataset_006_rep01 --no-miceforest --num-cpus 2
```

The smoke target: `dataset_006_rep01` / MCAR / 10% / Mean must give
`RMSE_continuous = 2.2795752629683292`, **not** `2.281571182876898`. That single number
distinguishes the corrected code from the defective code.

`Random` and `miceforest` draw stochastically during new-row transformation, and their
per-cell seeds come from a SHA-256 digest of
`(global_seed, dataset_id, scenario_id, split, original row key, column name)`. A fixed
record's imputed values therefore do not change when other rows are added, removed or
reordered, or when the work is batched differently. That is asserted by
`tests/test_inductive_imputation.py` and is worth re-checking if worker counts change.

---

## 9. Stale on completion

Everything below describes the superseded run until it is rebuilt.

| Artifact | Why |
|---|---|
| Every stage 05 and 06 figure and stats file | The underlying numbers changed |
| **Every stage 04 figure and stats file** | No stage 04 *value* changes, but the rankings de-duplicate: pure-continuous CD diagrams now compare 12 methods, not 21 |
| The knowledge DB and all compiled recommendations | Schema 2.0, corrected evidence |
| `results/presentation_v4/` | Derived from the superseded run |
| Both decks | See below |
| Out-of-sample numbers and method counts in `Methods.md` and the stage READMEs | Rechecked, not merely edited — counts are now conditional on stage and feature mix |

### The decks need code changes, not just a rebuild

Both decks share one provenance surface, `presentation/deck_numbers.py:collect()`, and
neither builder holds a literal number. Four things there still point at the old world:

1. `presentation/deck_numbers.py:49` — `DISCRETE_ANALYSIS = "discrete_subset_22methods_180datasets"`.
   That analysis key no longer exists in `method_ranking_honest.csv`. The CSV now carries
   four analyses: the primary, and one `within_<mix>_<n>methods_<n>datasets` per feature mix.
2. `presentation/build_presentation.py:1161` — cites `figS1_discrete_subset_effects.png`,
   a retired filename. There are now three `figS1_effects_<mix>.png`.
3. `presentation/deck_numbers.py` uses `GT_F1` as the stage-06 metric throughout
   (lines 285, 383–384, 676, 690, 724–746, 768–812). The primary outcome is now
   `Internal_F1` (the operational holdout), with `GT_F1` as the clean-test diagnostic.
   `W_LADDER`'s stage-06 entry names `GT_F1` too.
4. `presentation/build_chapter_deck.py:2762` reads `bc['levels']['independent']`, and the
   SoftImpute spotlight slide needs a new subject — SoftImpute has no stage 05 or 06 result
   to spotlight.

Fix those first, then rebuild in this order and confirm the QA output:

```bash
python presentation/build_chapter_deck.py
python presentation/qa_chapter_deck.py        # must print: clean.
python presentation/build_presentation.py
```

Numbers are re-read from `results/` on every build, but the takeaway **titles** are literal
strings. After a rerun that moves a result materially, re-read the directional claims — a
title can go stale while every number on the slide is correct. §10 says which directional
claims the probe already shows are at risk: any slide naming a single best method, and any
slide describing `Random`'s continuous performance.

---

## 10. The bias probe — result

The probe ran locally on 2026-09-18 and finished all 9 work-units. It regenerated stage 05
under the corrected code for 9 datasets — one per (feature mix × correlation) cell — across
all 3 mechanisms and all 5 rates, every scheduled method except miceforest, 1,620 rows, zero
residual NaN. It then joined those rows against the saved defective
`results/train_test_imputation/imputation_results.csv` on
`Dataset_ID, Mechanism, Missingness_Rate_Pct, Method`. Outputs are in `results/bias_probe/`.

Sign convention below: **positive = the defect made the method look better than it is.**

### The defect is not a uniform optimistic bias

| Feature type | Direction | Reading |
|---|---|---|
| Continuous, `Random` | **+4.50 RMSE** mean (old 8.19 → corrected 12.69), worse in 92% of cells | The one large optimistic bias |
| Continuous, all 17 other methods | **−0.015 to −0.151 RMSE** — correcting *improves* the score | The defect made them look **worse** |
| Binary | **−0.002 to −0.091** accuracy | Defect made them look worse |
| Categorical | **−0.002 to −0.083** accuracy | Defect made them look worse |

Fitting on a 20% test half that is itself 10–50% masked is a *smaller, noisier* fit than
fitting on the 80% train half. For every method that estimates a statistic — Mean, Median,
Mode, KNN neighbors, the MICE and IterativeImputer column models — the sample-size penalty
of the test half outweighs whatever leakage advantage it buys, so the defective numbers are
mildly **pessimistic**. `Random` inverts this because it draws uniformly from the fitted
frame's per-column min/max: the test half's observed range is narrower and closer to the
missing cells' true range, so the defect handed `Random` an advantage worth 4.5 RMSE.

The discrete bias concentrates in MNAR: binary mean bias is −0.005 under MCAR, −0.016 under
MAR, **−0.184 under MNAR**. Rate and correlation structure barely move it (binary −0.063 to
−0.074 across all five rates). Continuous bias is dominated by `Random`, so its pooled
stratum means are not interpretable on their own; read `bias_probe_by_method.csv` instead.

### Rankings move, and the top method inverts in three of five comparisons

`bias_probe_ranking.csv` (discrete, pooled) and
`bias_probe_ranking_continuous_by_mix.csv` (continuous). Continuous is reported per feature
mix because the stage-05 schedule is disjoint across mixes — a pooled common support keeps
0 blocks (CLAUDE.md §15).

| Comparison | n methods | Spearman ρ | Top method old → new |
|---|---:|---:|---|
| Continuous, pure_continuous | 10 | 0.976 | IterativeImputer (5) → **MICE-Linear (5)** |
| Continuous, mixed | 13 | 0.978 | IterativeImputer (5) → IterativeImputer (5) |
| Continuous, binary_heavy | 13 | 0.984 | IterativeImputer (5) → IterativeImputer (5) |
| Binary (`Accuracy_binary`) | 13 | **0.679** | IterativeImputer (10) → **IterativeImputer (5)** |
| Categorical (`Accuracy_categorical`) | 13 | 0.943 | IterativeImputer (5) → **MICE-Linear (10)** |

The top-five set changes in all five. The iterative family stays on top everywhere, so the
headline claim — iterative imputation beats the simple baselines — survives. What does not
survive is any sentence naming a single winner, any specific RMSE or accuracy value, and any
statement about `Random`'s continuous performance, which was overstated by a wide margin.
The binary ρ of 0.679 is the weakest link and the one to re-check first after the rerun.

### What this changes and what it does not

It sizes the narrative revision. It does **not** license reusing any defective number. The
probe is 9 of 270 datasets, excludes miceforest and (by design) SoftImpute, and compares
against a saved CSV that still carries the pre-de-duplication labels, so its own rankings are
provisional too. Every value in this section is superseded by the rerun.
