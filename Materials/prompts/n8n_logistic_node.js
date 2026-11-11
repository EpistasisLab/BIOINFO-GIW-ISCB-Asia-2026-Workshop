// Logistic Regression: a fixed, deterministic step. No language model is involved: the same predictors always give the same numbers.
// Recipe: keep valid predictors -> 70/30 train/test split by patient_id (no randomness) -> 5-fold cross-validation inside the
// training set -> final fit on the training set, scored once on the test set. Each fit: median imputation, standardization,
// L2-regularized logistic regression (C = 1).
const META = {
  "age": "integer",
  "sex": "binary",
  "prior_mi_count": "ordinal",
  "exertional_angina_history": "ordinal",
  "angina_functional_class": "ordinal",
  "recent_coronary_disease": "categorical",
  "family_history_coronary_disease": "binary",
  "hypertension_stage": "ordinal",
  "symptomatic_hypertension": "binary",
  "hypertension_duration": "ordinal",
  "prior_heart_failure": "categorical",
  "history_arrhythmia": "binary",
  "history_premature_atrial_contractions": "binary",
  "history_premature_ventricular_contractions": "binary",
  "history_paroxysmal_atrial_fibrillation": "binary",
  "history_persistent_atrial_fibrillation": "binary",
  "history_ventricular_fibrillation": "binary",
  "history_ventricular_tachycardia": "binary",
  "history_av_block_1st_degree": "binary",
  "history_av_block_3rd_degree": "binary",
  "history_lbbb_anterior_branch": "binary",
  "history_incomplete_lbbb": "binary",
  "history_complete_lbbb": "binary",
  "history_incomplete_rbbb": "binary",
  "history_complete_rbbb": "binary",
  "diabetes": "binary",
  "obesity": "binary",
  "thyrotoxicosis": "binary",
  "chronic_bronchitis": "binary",
  "obstructive_chronic_bronchitis": "binary",
  "asthma": "binary",
  "chronic_pneumonia": "binary",
  "pulmonary_tuberculosis": "binary",
  "systolic_bp_emergency_team": "real",
  "diastolic_bp_emergency_team": "real",
  "systolic_bp_icu": "real",
  "diastolic_bp_icu": "real",
  "pulmonary_edema_at_admission": "binary",
  "cardiogenic_shock_at_admission": "binary",
  "atrial_fibrillation_at_admission": "binary",
  "supraventricular_tachycardia_at_admission": "binary",
  "ventricular_tachycardia_at_admission": "binary",
  "ventricular_fibrillation_at_admission": "binary",
  "anterior_mi": "ordinal",
  "lateral_mi": "ordinal",
  "inferior_mi": "ordinal",
  "posterior_mi": "ordinal",
  "right_ventricular_mi": "binary",
  "ecg_rhythm_sinus_normal": "binary",
  "ecg_rhythm_atrial_fibrillation": "binary",
  "ecg_rhythm_atrial": "binary",
  "ecg_rhythm_idioventricular": "binary",
  "ecg_rhythm_sinus_tachycardia": "binary",
  "ecg_rhythm_sinus_bradycardia": "binary",
  "ecg_premature_atrial_contractions": "binary",
  "ecg_frequent_premature_atrial_contractions": "binary",
  "ecg_premature_ventricular_contractions": "binary",
  "ecg_frequent_premature_ventricular_contractions": "binary",
  "ecg_paroxysmal_atrial_fibrillation": "binary",
  "ecg_persistent_atrial_fibrillation": "binary",
  "ecg_supraventricular_tachycardia": "binary",
  "ecg_ventricular_tachycardia": "binary",
  "ecg_ventricular_fibrillation": "binary",
  "ecg_sinoatrial_block": "binary",
  "ecg_av_block_1st_degree": "binary",
  "ecg_av_block_2nd_degree_mobitz_1": "binary",
  "ecg_av_block_2nd_degree_mobitz_2": "binary",
  "ecg_av_block_3rd_degree": "binary",
  "ecg_lbbb_anterior_branch": "binary",
  "ecg_lbbb_posterior_branch": "binary",
  "ecg_incomplete_lbbb": "binary",
  "ecg_complete_lbbb": "binary",
  "ecg_incomplete_rbbb": "binary",
  "ecg_complete_rbbb": "binary",
  "fibrinolysis_celiasum_750k_iu": "binary",
  "fibrinolysis_celiasum_1m_iu": "binary",
  "fibrinolysis_celiasum_3m_iu": "binary",
  "fibrinolysis_streptase": "binary",
  "fibrinolysis_celiasum_500k_iu": "binary",
  "fibrinolysis_celiasum_250k_iu": "binary",
  "fibrinolysis_streptodecase_1_5m_iu": "binary",
  "hypokalemia": "binary",
  "serum_potassium": "real",
  "hypernatremia": "binary",
  "serum_sodium": "real",
  "serum_alt": "real",
  "serum_ast": "real",
  "serum_cpk": "real",
  "white_blood_cell_count": "real",
  "esr": "real",
  "time_to_hospital": "ordinal",
  "pain_relapse_day_1": "ordinal",
  "pain_relapse_day_2": "ordinal",
  "pain_relapse_day_3": "ordinal",
  "opioids_emergency_team": "binary",
  "nsaids_emergency_team": "binary",
  "lidocaine_emergency_team": "binary",
  "iv_nitrates_icu": "binary",
  "opioids_icu_day_1": "ordinal",
  "opioids_icu_day_2": "ordinal",
  "opioids_icu_day_3": "ordinal",
  "nsaids_icu_day_1": "ordinal",
  "nsaids_icu_day_2": "ordinal",
  "nsaids_icu_day_3": "ordinal",
  "lidocaine_icu": "binary",
  "beta_blockers_icu": "binary",
  "calcium_channel_blockers_icu": "binary",
  "heparin_icu": "binary",
  "aspirin_icu": "binary",
  "ticlopidine_icu": "binary",
  "pentoxifylline_icu": "binary"
};   // predictor name -> type, for every feature in our dataset (generated from the data dictionary)

const OUTCOME = 'heart_failure', ID = 'patient_id', C = 1, FOLDS = 5, MAX_MISSING_PCT = 30;
const isMissing = (v) => v === null || v === undefined || v === '' || Number.isNaN(Number(v));
const num = (v) => (isMissing(v) ? NaN : Number(v));
const mean = (a) => a.reduce((s, v) => s + v, 0) / a.length;
const sd0 = (a) => { const m = mean(a); return Math.sqrt(mean(a.map((v) => (v - m) ** 2))); };
const median = (a) => { const s = a.filter((v) => !Number.isNaN(v)).sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };

// ---- Tidy a model's Markdown so that it nests under our own headings: drop a document title, push its headings down to level 3,
// and rescale bullet indentation to 4 spaces per level (the Markdown converter needs that to show sub-bullets)
function tidyMarkdown(text) {
  const lines = String(text ?? '').split('\n');
  let fence = false;
  const isHeading = lines.map((l) => { if (/^\s*```/.test(l)) { fence = !fence; return false; } return !fence && /^#{1,6}\s/.test(l); });
  const level = (l) => l.match(/^#+/)[0].length;
  const headings = lines.map((l, i) => i).filter((i) => isHeading[i]);
  const title = headings.length > 1 && level(lines[headings[0]]) === 1 && headings.filter((i) => level(lines[i]) === 1).length === 1 ? headings[0] : -1;
  const minLevel = Math.min(6, ...headings.filter((i) => i !== title).map((i) => level(lines[i])));
  const shift = headings.length ? Math.max(0, 3 - minLevel) : 0;
  fence = false;
  const bullets = lines.map((l) => { if (/^\s*```/.test(l)) { fence = !fence; return null; } return fence ? null : l.match(/^( +)([-*+]|\d+[.)])\s/); });
  const step = Math.min(...bullets.filter(Boolean).map((m) => m[1].length));
  const out = [];
  lines.forEach((l, i) => {
    if (i === title) return;
    if (isHeading[i]) out.push('#'.repeat(Math.min(6, level(l) + shift)) + l.slice(level(l)));
    else if (bullets[i] && step < 4) out.push(' '.repeat(Math.round(bullets[i][1].length / step) * 4) + l.slice(bullets[i][1].length));
    else out.push(l);
  });
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

// ---- 1. What the Data Analyst asked for: its answer starts with a line "FEATURES: name1, name2, ..."; the rest is its report
const answerText = String($('Data Analyst').first().json.output ?? '');
const featuresLine = answerText.match(/^[ \t>*#_-]*FEATURES[ \t*_]*:[ \t*_]*(.+)$/mi);
const requested = featuresLine
  ? featuresLine[1].split(/[,;\s]+/).map((n) => n.replace(/^[`'"*_\[\]().]+|[`'"*_\[\]().]+$/g, '')).filter(Boolean)
  : [];
const report = tidyMarkdown(answerText.replace(featuresLine ? featuresLine[0] : '', ''));
const scout_markdown = tidyMarkdown($('Literature Scout').first().json.output);

// ---- 2. The patients, in a fixed order, with a data check
const rows = $input.all().map((item) => item.json).sort((a, b) => num(a[ID]) - num(b[ID]));
const y = rows.map((r) => num(r[OUTCOME]));
const events = y.reduce((s, v) => s + (v === 1 ? 1 : 0), 0);
if (rows.length !== 1700 || events !== 394) {
  throw new Error(`The data table has ${rows.length} rows and ${events} heart failure cases; expected 1,700 and 394. Check that you imported Data/mi_heart_failure.csv unchanged and selected that table.`);
}

// ---- 3. The split: number cases and non-cases separately; positions 0-6 of every 10 are TRAIN, the rest TEST
const seen = [0, 0];
const train = [], test = [];
rows.forEach((r, i) => { const pos = seen[y[i]]++; (pos % 10 < 7 ? train : test).push(i); });
const yTrain = train.map((i) => y[i]), yTest = test.map((i) => y[i]);

// ---- 4. Which requested predictors can we use?
const used = [], dropped = [], listed = new Set();
for (const name of requested) {
  if (listed.has(name)) continue;
  listed.add(name);
  let reason = null;
  if (!(name in META)) reason = name === OUTCOME ? 'is the outcome' : 'not a predictor in our dataset';
  else if (/_day_\d$/.test(name)) reason = 'known only after admission';
  else {
    const missing = 100 * train.filter((i) => Number.isNaN(num(rows[i][name]))).length / train.length;
    if (missing > MAX_MISSING_PCT) reason = `${Math.round(missing)}% missing in the training split`;
  }
  if (reason) dropped.push({ name, reason }); else used.push(name);
}
const model = { valid_features: used, dropped, n_train: train.length, n_test: test.length,
                events_train: yTrain.reduce((s, v) => s + v, 0), events_test: yTest.reduce((s, v) => s + v, 0) };
if (!used.length) {
  model.model_fitted = false;
  const why = requested.length ? 'none of the predictors the Data Analyst listed could be used' : "the Data Analyst's answer has no FEATURES line, or the line lists no variables";
  const text = `- Patients: ${model.n_train} train, ${model.n_test} test.\n- No model was fitted: ${why}.` +
    (dropped.length ? `\n- Dropped: ${dropped.map((d) => `${d.name} (${d.reason})`).join('; ')}.` : '');
  return [{ json: { report, scout_markdown, features: requested, model, model_markdown: text } }];
}

// ---- 5. The predictors as numbers (a categorical variable becomes 0/1 columns for its training levels; the lowest is the reference)
const columns = [];   // { name, values: one number per patient, NaN if missing }
for (const name of used) {
  const values = rows.map((r) => num(r[name]));
  if (META[name] === 'categorical') {
    const levels = [...new Set(train.map((i) => values[i]).filter((v) => !Number.isNaN(v)))].sort((a, b) => a - b).slice(1);
    for (const level of levels) columns.push({ name: `${name}=${level}`, values: values.map((v) => (Number.isNaN(v) ? NaN : v === level ? 1 : 0)) });
  } else columns.push({ name, values });
}
const p = columns.length;

// Median imputation and standardization, both learned on the fit rows only. Returns scaled rows for the fit and other rows.
function prepare(fitIdx, otherIdx) {
  const meds = columns.map((c) => median(fitIdx.map((i) => c.values[i])));
  const filled = (i) => columns.map((c, j) => (Number.isNaN(c.values[i]) ? meds[j] : c.values[i]));
  const fitRows = fitIdx.map(filled);
  const mu = columns.map((_, j) => mean(fitRows.map((r) => r[j])));
  const sd = columns.map((_, j) => sd0(fitRows.map((r) => r[j])) || 1);
  const scale = (r) => r.map((v, j) => (v - mu[j]) / sd[j]);
  return { fit: fitRows.map(scale), other: otherIdx.map((i) => scale(filled(i))), sd };
}

// ---- 6. L2-regularized logistic regression by Newton's method (intercept not penalized)
function solve(A, b) {   // Gaussian elimination with partial pivoting
  const n = b.length, M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    [M[c], M[piv]] = [M[piv], M[c]];
    for (let r = c + 1; r < n; r++) { const f = M[r][c] / M[c][c]; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) { let s = M[r][n]; for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k]; x[r] = s / M[r][r]; }
  return x;
}
const sigmoid = (z) => 1 / (1 + Math.exp(-z));
function fitLogistic(X, t) {
  const n = X.length, lambda = 1 / C;
  let w = new Array(p + 1).fill(0);   // w[0] = intercept
  const logit = (row, v) => v[0] + row.reduce((s, x, j) => s + x * v[j + 1], 0);
  const objective = (v) => X.reduce((s, row, i) => { const z = logit(row, v); return s + Math.log1p(Math.exp(-Math.abs(z))) + Math.max(z, 0) - t[i] * z; }, 0) + 0.5 * lambda * v.slice(1).reduce((s, a) => s + a * a, 0);
  for (let iter = 0; iter < 100; iter++) {
    const grad = new Array(p + 1).fill(0), H = Array.from({ length: p + 1 }, () => new Array(p + 1).fill(0));
    X.forEach((row, i) => {
      const mu = sigmoid(logit(row, w)), wt = mu * (1 - mu), z = [1, ...row];
      for (let a = 0; a <= p; a++) { grad[a] += (mu - t[i]) * z[a]; for (let b = 0; b <= p; b++) H[a][b] += wt * z[a] * z[b]; }
    });
    for (let a = 1; a <= p; a++) { grad[a] += lambda * w[a]; H[a][a] += lambda; }
    const step = solve(H, grad);
    let scale = 1; const before = objective(w);
    while (scale > 1e-8 && objective(w.map((v, a) => v - scale * step[a])) > before + 1e-12) scale /= 2;
    w = w.map((v, a) => v - scale * step[a]);
    if (Math.max(...step.map((s) => Math.abs(s * scale))) < 1e-10) break;
  }
  return { b: w[0], w: w.slice(1), predict: (rows) => rows.map((row) => sigmoid(logit(row, w))) };
}

// ---- 7. Metrics: AUC (ties averaged), PR-AUC (average precision), Brier
function auc(t, s) {
  const order = s.map((v, i) => i).sort((a, b) => s[a] - s[b]), rank = new Array(s.length);
  for (let i = 0; i < order.length;) { let j = i; while (j + 1 < order.length && s[order[j + 1]] === s[order[i]]) j++; for (let k = i; k <= j; k++) rank[order[k]] = (i + j) / 2 + 1; i = j + 1; }
  const pos = t.reduce((a, v) => a + v, 0), neg = t.length - pos;
  return (t.reduce((a, v, i) => a + (v === 1 ? rank[i] : 0), 0) - pos * (pos + 1) / 2) / (pos * neg);
}
function averagePrecision(t, s) {
  const order = s.map((v, i) => i).sort((a, b) => s[b] - s[a]), pos = t.reduce((a, v) => a + v, 0);
  let tp = 0, fp = 0, ap = 0, lastRecall = 0;
  for (let i = 0; i < order.length;) {
    let j = i; while (j + 1 < order.length && s[order[j + 1]] === s[order[i]]) j++;
    for (let k = i; k <= j; k++) { if (t[order[k]] === 1) tp++; else fp++; }
    const recall = tp / pos; ap += (recall - lastRecall) * (tp / (tp + fp)); lastRecall = recall; i = j + 1;
  }
  return ap;
}
const brier = (t, s) => mean(s.map((v, i) => (v - t[i]) ** 2));
const scores = (t, s) => ({ auc: auc(t, s), pr_auc: averagePrecision(t, s), brier: brier(t, s) });

// ---- 8. 5-fold cross-validation inside the training set (the j-th case and the j-th non-case go to fold j mod 5)
const counter = [0, 0], fold = train.map((i) => counter[y[i]]++ % FOLDS);
const cv = [];
for (let k = 0; k < FOLDS; k++) {
  const fitPos = train.map((_, a) => a).filter((a) => fold[a] !== k), outPos = train.map((_, a) => a).filter((a) => fold[a] === k);
  const prep = prepare(fitPos.map((a) => train[a]), outPos.map((a) => train[a]));
  const fit = fitLogistic(prep.fit, fitPos.map((a) => yTrain[a]));
  cv.push(scores(outPos.map((a) => yTrain[a]), fit.predict(prep.other)));
}

// ---- 9. Final fit on the whole training set, scored once on the test set
const prep = prepare(train, test);
const final = fitLogistic(prep.fit, yTrain);
const testScores = scores(yTest, final.predict(prep.other));
const odds = columns.map((c, j) => ({ feature: c.name, std_coef: final.w[j], odds_ratio: Math.exp(final.w[j] / prep.sd[j]) }))
  .sort((a, b) => Math.abs(b.std_coef) - Math.abs(a.std_coef));
const col = (key) => cv.map((s) => s[key]);
Object.assign(model, {
  model_fitted: true, columns: p, events_per_column: model.events_train / p,
  cv_auc_mean: mean(col('auc')), cv_auc_sd: sd0(col('auc')), cv_pr_auc_mean: mean(col('pr_auc')), cv_pr_auc_sd: sd0(col('pr_auc')),
  cv_brier_mean: mean(col('brier')), cv_brier_sd: sd0(col('brier')),
  test_auc: testScores.auc, test_pr_auc: testScores.pr_auc, test_brier: testScores.brier,
  train_auc: auc(yTrain, final.predict(prep.fit)), no_skill_pr_auc: mean(yTest), odds_ratios: odds,
});

// ---- 10. The text for the report (Part 3)
const f3 = (v) => v.toFixed(3);
const top = odds.slice(0, 8).map((o) => `| \`${o.feature}\` | ${o.odds_ratio.toFixed(2)} | ${o.std_coef.toFixed(2)} |`).join('\n');
const model_markdown = [
  `- **Patients:** ${model.n_train.toLocaleString('en-US')} train (${model.events_train} with heart failure) and ${model.n_test} test (${model.events_test} with heart failure).`,
  `- **Predictors used (${used.length}):** ${used.map((n) => '`' + n + '`').join(', ')}.`,
  dropped.length ? `- **Dropped:** ${dropped.map((d) => `\`${d.name}\` (${d.reason})`).join('; ')}.` : null,
  `- **Model columns:** ${p} (${model.events_per_column.toFixed(1)} training events per column).`,
  `- **5-fold cross-validation in the training set:** AUC ${f3(model.cv_auc_mean)} ± ${f3(model.cv_auc_sd)}, PR-AUC ${f3(model.cv_pr_auc_mean)}, Brier ${f3(model.cv_brier_mean)}.`,
  `- **Held-out test set:** AUC ${f3(model.test_auc)}, PR-AUC ${f3(model.test_pr_auc)} (a model with no skill scores ${f3(model.no_skill_pr_auc)}), Brier ${f3(model.test_brier)}.`,
  `- **Training-set AUC** (on the data the model learned from): ${f3(model.train_auc)}.`,
  '',
  '| Predictor | Odds ratio per unit | Standardized coefficient |',
  '|---|---|---|',
  top,
  '',
  '*L2-regularized logistic regression (C = 1), median imputation, standardized predictors. Odds ratios are shrunk by the penalty and have no confidence intervals. The test AUC comes from a single split, so it is noisy; a cross-validation AUC well above it suggests the predictors were chosen after looking at the training data.*',
].filter((line) => line !== null).join('\n');

return [{ json: { report, scout_markdown, features: requested, model, model_markdown } }];
