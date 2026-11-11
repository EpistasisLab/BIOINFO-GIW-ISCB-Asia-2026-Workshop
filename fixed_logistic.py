"""A fixed, deterministic logistic-regression model for the heart failure data.

This is the Python twin of the "Logistic Regression" Code node in the n8n workflow (Session 2a). Given a list of
predictor names, it always returns the same numbers: no random seeds, no language model. Use it to check the node,
or as the reference scorer when you rerun the workflow in another platform.

The recipe (the n8n node follows exactly the same steps):
 1. Keep only valid predictors: a feature in the data dictionary, known at admission, at most 30% missing in the
    training split. Everything else is dropped, with a reason.
 2. Split the patients 70/30 without randomness: order patients by patient_id, number the cases and the non-cases
    separately 0, 1, 2, ...; positions with (number mod 10) < 7 are TRAIN, the rest are TEST.
 3. 5-fold cross-validation inside the training set: within train, the j-th case and the j-th non-case (by patient_id)
    go to fold (j mod 5).
 4. For each fit: median imputation, standardization, L2-regularized logistic regression (C = 1).
 5. Final fit on the whole training set, scored once on the test set.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

ROOT = Path(__file__).parent
OUTCOME, ID = "heart_failure", "patient_id"
TRAIN_POSITIONS, SPLIT_PERIOD = 7, 10       # positions 0-6 of every 10 go to train
FOLDS = 5
MAX_MISSING_PCT = 30.0
C = 1.0


def load_data(csv_path=None, dictionary_path=None):
    """The patient table and the data dictionary (variable name -> column description)."""
    df = pd.read_csv(csv_path or ROOT / "Data" / "mi_heart_failure.csv")
    columns = json.loads(Path(dictionary_path or ROOT / "Data" / "dict_heart_failure.json").read_text())["columns"]
    return df, {col["name"]: col for col in columns}


def known_at_admission(name):
    # UCI guidance: the day 1-3 hospital variables are only known at the end of that day
    return re.search(r"_day_\d$", name) is None


def _positions(df):
    """Patient position within its class (cases and non-cases numbered separately, ordered by patient_id)."""
    ordered = df.sort_values(ID)
    return ordered.groupby(OUTCOME).cumcount().reindex(df.index)


def split_patients(df):
    """Deterministic stratified 70/30 split. Returns (train_ids, test_ids) as lists of patient_id."""
    position = _positions(df)
    is_train = (position % SPLIT_PERIOD) < TRAIN_POSITIONS
    return df.loc[is_train, ID].tolist(), df.loc[~is_train, ID].tolist()


def _fold_of(train):
    """Fold number (0-4) for every training patient: the j-th case and the j-th non-case go to fold j mod 5."""
    return _positions(train) % FOLDS


def _design(df, features, dictionary, train):
    """Predictors as numbers. A categorical variable becomes 0/1 columns for its levels in the TRAINING split
    (the lowest level is the reference); a missing value stays missing."""
    columns = {}
    for name in features:
        values = pd.to_numeric(df[name], errors="coerce").astype(float)
        if dictionary[name]["type"] == "categorical":
            for level in sorted(pd.to_numeric(train[name], errors="coerce").dropna().unique())[1:]:
                columns[f"{name}={level:g}"] = ((values == level).astype(float)).where(values.notna())
        else:
            columns[name] = values
    return pd.DataFrame(columns)


def _prepare(X_fit, X_other):
    """Median imputation, then standardization (population SD), both learned on the fit part only."""
    medians = X_fit.median()
    fit, other = X_fit.fillna(medians), X_other.fillna(medians)
    mean, sd = fit.mean(), fit.std(ddof=0).replace(0, 1.0)
    return ((fit - mean) / sd).to_numpy(), ((other - mean) / sd).to_numpy(), sd


def _fit(X, y):
    return LogisticRegression(C=C, penalty="l2", solver="lbfgs", tol=1e-10, max_iter=5000).fit(X, y)


def _scores(y, p):
    return {"auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "brier": brier_score_loss(y, p)}


def parse_features_line(answer):
    """The Data Analyst's answer starts with a line 'FEATURES: name1, name2, ...'. Returns (the predictor names, the rest of
    the answer). The n8n Code node uses the same rule."""
    match = re.search(r"^[ \t>*#_-]*FEATURES[ \t*_]*:[ \t*_]*(.+)$", answer, re.I | re.M)
    names = []
    if match:
        for name in re.split(r"[,;\s]+", match.group(1)):
            name = re.sub(r"^[`'\"*_\[\]().]+|[`'\"*_\[\]().]+$", "", name)
            if name:
                names.append(name)
    return names, (answer.replace(match.group(0), "", 1) if match else answer).strip()


def tidy_markdown(text):
    """Tidy a model's Markdown so it nests under our own headings: drop a document title (a single H1), push its headings
    down to level 3, and rescale bullet indentation to 4 spaces per level. The n8n Code node does the same."""
    lines = str(text or "").split("\n")
    fence, is_heading = False, []
    for line in lines:
        if re.match(r"^\s*```", line):
            fence = not fence
            is_heading.append(False)
        else:
            is_heading.append(not fence and bool(re.match(r"^#{1,6}\s", line)))
    level = lambda line: len(re.match(r"^#+", line).group(0))
    headings = [i for i, flag in enumerate(is_heading) if flag]
    title = headings[0] if len(headings) > 1 and level(lines[headings[0]]) == 1 and sum(level(lines[i]) == 1 for i in headings) == 1 else -1
    min_level = min([6] + [level(lines[i]) for i in headings if i != title])
    shift = max(0, 3 - min_level) if headings else 0
    fence, bullets = False, []
    for line in lines:
        if re.match(r"^\s*```", line):
            fence = not fence
            bullets.append(None)
        else:
            bullets.append(None if fence else re.match(r"^( +)([-*+]|\d+[.)])\s", line))
    indents = [len(m.group(1)) for m in bullets if m]
    step = min(indents) if indents else float("inf")
    out = []
    for i, line in enumerate(lines):
        if i == title:
            continue
        if is_heading[i]:
            out.append("#" * min(6, level(line) + shift) + line[level(line):])
        elif bullets[i] and step < 4:
            out.append(" " * (int(len(bullets[i].group(1)) / step + 0.5) * 4) + line[len(bullets[i].group(1)):])
        else:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def valid_features(features, df, dictionary, train):
    """Split the requested predictors into those we can use and those dropped, with a reason for each."""
    keep, dropped, seen = [], [], set()
    for name in features:
        if name in seen:
            continue
        seen.add(name)
        if name not in dictionary or dictionary[name]["role"] != "feature":
            reason = "is the outcome" if name == OUTCOME else "not a predictor in our dataset"
        elif not known_at_admission(name):
            reason = "known only after admission"
        elif (missing := 100 * train[name].isna().mean()) > MAX_MISSING_PCT:
            reason = f"{missing:.0f}% missing in the training split"
        else:
            keep.append(name)
            continue
        dropped.append({"name": name, "reason": reason})
    return keep, dropped


def fixed_logistic_model(features, csv_path=None, dictionary_path=None):
    """Fit the fixed model on the requested predictors. Returns a dict of metrics (cross-validated on the training
    split, and on the held-out test split), odds ratios, and the predictors that were dropped."""
    df, dictionary = load_data(csv_path, dictionary_path)
    if len(df) != 1700 or int(df[OUTCOME].sum()) != 394:
        raise ValueError(f"Unexpected data: {len(df)} rows and {int(df[OUTCOME].sum())} cases (expected 1,700 and 394).")
    train_ids, _ = split_patients(df)
    is_train = df[ID].isin(set(train_ids))
    train, test = df[is_train], df[~is_train]
    keep, dropped = valid_features(list(features), df, dictionary, train)
    result = {"valid_features": keep, "dropped": dropped, "n_train": len(train), "n_test": len(test),
              "events_train": int(train[OUTCOME].sum()), "events_test": int(test[OUTCOME].sum())}
    if not keep:
        return {**result, "model_fitted": False}

    X = _design(df, keep, dictionary, train)
    X_train, X_test, y_train, y_test = X[is_train], X[~is_train], train[OUTCOME].to_numpy(), test[OUTCOME].to_numpy()

    folds, fold_scores = _fold_of(train).to_numpy(), []
    for k in range(FOLDS):
        fit_part = folds != k
        A, B, _ = _prepare(X_train[fit_part], X_train[~fit_part])
        model = _fit(A, y_train[fit_part])
        fold_scores.append(_scores(y_train[~fit_part], model.predict_proba(B)[:, 1]))
    cv = pd.DataFrame(fold_scores)

    A, B, sd = _prepare(X_train, X_test)
    model = _fit(A, y_train)
    test_scores = _scores(y_test, model.predict_proba(B)[:, 1])
    train_auc = roc_auc_score(y_train, model.predict_proba(A)[:, 1])
    odds = [{"feature": name, "std_coef": float(c), "odds_ratio": float(np.exp(c / s))}
            for name, c, s in zip(X.columns, model.coef_[0], sd)]
    odds.sort(key=lambda row: -abs(row["std_coef"]))
    return {**result, "model_fitted": True, "columns": X.shape[1], "events_per_column": result["events_train"] / X.shape[1],
            "cv_auc_mean": cv["auc"].mean(), "cv_auc_sd": cv["auc"].std(ddof=0),
            "cv_pr_auc_mean": cv["pr_auc"].mean(), "cv_pr_auc_sd": cv["pr_auc"].std(ddof=0),
            "cv_brier_mean": cv["brier"].mean(), "cv_brier_sd": cv["brier"].std(ddof=0),
            "test_auc": test_scores["auc"], "test_pr_auc": test_scores["pr_auc"], "test_brier": test_scores["brier"],
            "train_auc": train_auc, "no_skill_pr_auc": float(y_test.mean()), "odds_ratios": odds}


def summary_text(result):
    """The result as a few readable lines (the n8n node writes the same lines into the report)."""
    r = result
    lines = [f"Patients: {r['n_train']:,} train ({r['events_train']} with heart failure) and {r['n_test']:,} test ({r['events_test']} with heart failure)."]
    lines.append("Predictors used: " + (", ".join(r["valid_features"]) or "none") + ".")
    if r["dropped"]:
        lines.append("Dropped: " + "; ".join(f"{d['name']} ({d['reason']})" for d in r["dropped"]) + ".")
    if not r["model_fitted"]:
        lines.append("No model was fitted because none of the predictors could be used.")
        return "\n".join(lines)
    lines.append(f"Model columns: {r['columns']} ({r['events_per_column']:.1f} training events per column).")
    lines.append(f"5-fold cross-validation in the training set: AUC {r['cv_auc_mean']:.3f} ± {r['cv_auc_sd']:.3f}, "
                 f"PR-AUC {r['cv_pr_auc_mean']:.3f}, Brier {r['cv_brier_mean']:.3f}.")
    lines.append(f"Held-out test set: AUC {r['test_auc']:.3f}, PR-AUC {r['test_pr_auc']:.3f} (no-skill {r['no_skill_pr_auc']:.3f}), Brier {r['test_brier']:.3f}.")
    lines.append(f"Training-set AUC (fit to the data it learned from): {r['train_auc']:.3f}.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    requested = sys.argv[1:] or ["age", "sex", "diabetes", "prior_heart_failure", "anterior_mi"]
    print(summary_text(fixed_logistic_model(requested)))
