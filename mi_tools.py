"""Shared code for the agent modules: the MI data, four analysis tools, model setup, and run helpers.

Used by 02_agent_design_patterns.ipynb and 03_multi_agent_langgraph.ipynb. The four tools (`list_variables`, `profile_data`, `compare_groups`,
`train_model`) are ordinary Python functions that a LangChain agent can call. Their docstrings are what the
model reads, so they say exactly what each tool returns.
"""
import functools
import json
from importlib.metadata import version
import os
import re
import time
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, messages_from_dict, messages_to_dict
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from scipy import stats
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.simplefilter("ignore", ConvergenceWarning)      # statsmodels turns these back on at import; train() already handles failed fits

# ----------------------------------------------------------------------------------------------- data
ROOT = Path(__file__).parent
OUTCOME = "heart_failure"

df = pd.read_csv(ROOT / "Data" / "mi_heart_failure.csv")
DICT = {c["name"]: c for c in json.loads((ROOT / "Data" / "dict_heart_failure.json").read_text())["columns"]}
FEATURES = [name for name, col in DICT.items() if col["role"] == "feature"]


def known_at(name):
    # UCI guidance: the day 1-3 hospital variables are only known at the end of that day
    day = re.search(r"_day_(\d)$", name)
    return f"end of day {day.group(1)}" if day else "admission"


ADMISSION = [name for name in FEATURES if known_at(name) == "admission"]


def pct_missing(name):
    return 100 * df[name].isna().mean()


def code_labels(name):
    text = (DICT[name].get("codes") or "").split(". ")[0]
    return {int(k): v.strip() for k, v in re.findall(r"(\d+)=([^;]+)", text)}


def check_names(predictors):
    # Returns an error message the agent can act on, or None
    unknown = [p for p in predictors if p not in FEATURES]
    if unknown:
        return f"Unknown or not allowed variables: {', '.join(unknown)}. Use list_variables to find valid names."
    if not predictors:
        return "Give at least one predictor."
    return None


def design_matrix(predictors):
    """The predictors as numbers. Categorical variables become 0/1 columns (the lowest code is the reference)."""
    X = df[predictors].astype(float)
    for p in predictors:
        if DICT[p]["type"] == "categorical":
            codes = sorted(X[p].dropna().unique())[1:]
            dummies = pd.DataFrame({f"{p}={int(c)}": (X[p] == c).astype(float) for c in codes})
            dummies[X[p].isna()] = np.nan                     # a missing value stays missing
            X = X.drop(columns=p).join(dummies)
    return X


def p_text(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


ModelType = Literal["logistic", "penalized_logistic", "random_forest", "gradient_boosting"]
MissingStrategy = Literal["complete_case", "impute", "native"]


def safe(function):
    """Make a tool return an error message instead of crashing, so the agent can read it and try again."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            return f"{function.__name__} failed ({type(error).__name__}: {error}). Check the inputs and try again."
    return wrapper


# ----------------------------------------------------------------------------------------------- tools
@tool(parse_docstring=True)
@safe
def list_variables(search: str = "", when_known: Literal["any", "admission"] = "any", max_missing_pct: float = 100) -> str:
    """List variables in the MI dataset with their type, when each is known, % missing, and meaning.

    Args:
        search: Only variables whose name or description contains this text (case-insensitive). Empty for all.
        when_known: "admission" for variables known when the patient arrives; "any" also includes variables known only at the end of hospital day 1, 2, or 3.
        max_missing_pct: Only variables with at most this percentage of missing values.
    """
    rows = []
    for name in FEATURES:
        col = DICT[name]
        text = f"{name} {col['description']}".lower()
        if search.lower() not in text or pct_missing(name) > max_missing_pct:
            continue
        if when_known == "admission" and known_at(name) != "admission":
            continue
        meaning = col["description"] + (f" ({col['units']})" if col.get("units") else "")
        if col.get("codes") and col["codes"] != "0=no; 1=yes":
            meaning += ". Codes: " + col["codes"].split(". ")[0]
        rows.append(f"{name} | {col['type']} | {known_at(name)} | {pct_missing(name):.1f}% missing | {meaning}")
    if not rows:
        return "No variables match."
    return f"{len(rows)} variables (name | type | known at | missing | meaning):\n" + "\n".join(rows)


@tool(parse_docstring=True)
@safe
def profile_data(predictors: list[str]) -> str:
    """Check what the data can support for a set of predictors: patients, events, missing data, and events per variable.

    Args:
        predictors: Variable names, for example ["age", "sex", "diabetes"].
    """
    if error := check_names(predictors):
        return error
    X = design_matrix(predictors)
    events = int(df[OUTCOME].sum())
    complete = X.notna().all(axis=1)
    complete_events = int(df.loc[complete, OUTCOME].sum())
    late = [p for p in predictors if known_at(p) != "admission"]
    high = [f"{p} ({pct_missing(p):.1f}%)" for p in predictors if pct_missing(p) > 30]
    lines = [
        f"Patients: {len(df):,}; heart failure events: {events} ({100 * events / len(df):.1f}%).",
        f"Predictors: {len(predictors)} ({X.shape[1]} model columns after encoding categorical variables).",
        f"Known only after admission: {', '.join(late) if late else 'none'}.",
        f"Complete cases (no missing predictor): {int(complete.sum()):,} patients, {complete_events} events.",
        f"Events per model column in complete cases: {complete_events / X.shape[1]:.1f} (logistic regression usually needs about 10 or more).",
        f"Predictors with more than 30% missing: {', '.join(high) if high else 'none'}.",
    ]
    if len(predictors) <= 20:
        lines.append("Missing per predictor: " + ", ".join(f"{p} {pct_missing(p):.1f}%" for p in predictors) + ".")
    return "\n".join(lines)


@tool(parse_docstring=True)
@safe
def compare_groups(variable: str, cutoff: float | None = None) -> str:
    """Compare heart failure between groups of patients for ONE variable (unadjusted, one variable at a time).

    Yes/no and coded variables: heart failure rate per code, with a chi-square test. Measurements (age, serum_potassium, ...): mean with and without heart failure, with a Welch t-test. With a cutoff, the variable is split into below / at or above the cutoff and the heart failure rates are compared (with a risk ratio).

    Args:
        variable: Exact variable name, for example "diabetes" or "age".
        cutoff: Optional. Split the variable at this value, for example 70 for age.
    """
    if error := check_names([variable]):
        return error
    col = DICT[variable]
    d = df[[variable, OUTCOME]].dropna()
    lines = [f"{variable}: {col['description']}. Patients with data: {len(d):,} ({len(df) - len(d)} missing, left out)."]
    if cutoff is None and col["type"] in ("real", "integer"):
        with_hf, without_hf = d.loc[d[OUTCOME] == 1, variable], d.loc[d[OUTCOME] == 0, variable]
        p = stats.ttest_ind(with_hf, without_hf, equal_var=False).pvalue
        lines.append(f"Mean {with_hf.mean():.2f} with heart failure vs {without_hf.mean():.2f} without ({p_text(p)}, Welch t-test).")
        return "\n".join(lines)
    if cutoff is not None:
        above = d[variable] >= cutoff
        groups = {f"below {cutoff:g}": ~above, f"{cutoff:g} or higher": above}
    else:
        labels = code_labels(variable)
        groups = {f"{int(c)} ({labels[int(c)]})" if int(c) in labels else f"{c:g}": d[variable] == c for c in sorted(d[variable].unique())}
    counts = {name: (int(mask.sum()), int(d.loc[mask, OUTCOME].sum())) for name, mask in groups.items()}
    if cutoff is not None and 0 in [n for n, _ in counts.values()]:
        return f"No patients fall on one side of the cutoff {cutoff:g}: {variable} ranges from {d[variable].min():g} to {d[variable].max():g}."
    for name, (n, hf) in counts.items():
        lines.append(f"  {name}: {n} patients, {hf} with heart failure ({100 * hf / n:.1f}%)")
    p = stats.chi2_contingency([[hf, n - hf] for n, hf in counts.values()], correction=False)[1]
    lines.append(f"Chi-square test: {p_text(p)}.")
    if cutoff is not None:
        (n0, hf0), (n1, hf1) = counts.values()
        ratio = f"{(hf1 / n1) / (hf0 / n0):.2f}" if hf0 else "not defined (no heart failure below the cutoff)"
        lines.append(f"Risk ratio ({cutoff:g} or higher vs below): {ratio}.")
    return "\n".join(lines)


CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)


def make_model(model_type, missing_strategy):
    steps = [SimpleImputer(strategy="median")] if missing_strategy == "impute" else []
    if model_type == "logistic":
        steps += [StandardScaler(), LogisticRegression(penalty=None, max_iter=2000)]
    elif model_type == "penalized_logistic":
        steps += [StandardScaler(), LogisticRegressionCV(penalty="l1", solver="liblinear", Cs=[0.01, 0.03, 0.1, 0.3, 1], cv=3, scoring="roc_auc")]
    elif model_type == "random_forest":
        steps += [RandomForestClassifier(n_estimators=200, min_samples_leaf=5, n_jobs=-1, random_state=0)]
    elif model_type == "gradient_boosting":
        steps += [HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=3, min_samples_leaf=20, random_state=0)]
    else:
        raise ValueError(f"unknown model_type {model_type}")
    return make_pipeline(*steps)


def describe_drivers(model, X, y, model_type, missing_strategy):
    if model_type == "logistic":
        # Odds ratios from statsmodels, so we also get confidence intervals
        data = X if missing_strategy == "complete_case" else X.fillna(X.median())
        try:
            fit = sm.Logit(y, sm.add_constant(data)).fit(disp=0, maxiter=200)
            assert fit.mle_retvals["converged"]
        except Exception:
            return "Odds ratios could not be estimated (the fit did not converge, usually too many predictors for the events); try penalized_logistic."
        table = pd.DataFrame({"OR": np.exp(fit.params), "lo": np.exp(fit.conf_int()[0]), "hi": np.exp(fit.conf_int()[1]), "p": fit.pvalues}).drop("const")
        lines = [f"  {name}: OR {r.OR:.2f} (95% CI {r.lo:.2f}-{r.hi:.2f}), {p_text(r.p)}" for name, r in table.sort_values("p").head(15).iterrows()]
        return "Adjusted odds ratios per 1-unit increase (15 smallest p-values):\n" + "\n".join(lines)
    if model_type == "penalized_logistic":
        fitted = clone(model).fit(X, y)
        coefs = pd.Series(fitted[-1].coef_[0], index=X.columns)
        kept = coefs[coefs != 0].sort_values(key=abs, ascending=False)
        lines = [f"  {name}: OR {np.exp(c):.2f} per 1 SD" for name, c in kept.head(15).items()]
        return f"L1 penalty kept {len(kept)} of {X.shape[1]} columns (strongest 15):\n" + "\n".join(lines)
    # Tree models: how much does AUC drop when one column is shuffled? (measured on the first test fold)
    train, test = next(iter(CV.split(X, y)))
    fitted = clone(model).fit(X.iloc[train], y.iloc[train])
    result = permutation_importance(fitted, X.iloc[test], y.iloc[test], scoring="roc_auc", n_repeats=3, random_state=0)
    top = pd.Series(result.importances_mean, index=X.columns).sort_values(ascending=False).head(10)
    return "Most important columns (mean drop in AUC when shuffled, first test fold):\n" + "\n".join(f"  {name}: {value:.3f}" for name, value in top.items())


def train(predictors, model_type, missing_strategy):
    """Cross-validate a model. Returns (text for the agent, numbers for our own checks)."""
    if error := check_names(predictors):
        return error, None
    if missing_strategy == "native" and model_type != "gradient_boosting":
        return "missing_strategy 'native' works only with model_type 'gradient_boosting'. Use 'complete_case' or 'impute' for this model.", None
    X, y = design_matrix(predictors), df[OUTCOME]
    if missing_strategy == "complete_case":
        keep = X.notna().all(axis=1)
        X, y = X[keep], y[keep]
    if y.sum() < 30 or (y == 0).sum() < 30:
        return f"Only {len(y)} patients ({int(y.sum())} events) are left, too few to fit a model. Use 'impute' or 'native', or fewer predictors.", None
    model = make_model(model_type, missing_strategy)
    cv = cross_validate(model, X, y, cv=CV, scoring={"auc": "roc_auc", "pr_auc": "average_precision", "brier": "neg_brier_score"})
    numbers = {"auc": cv["test_auc"].mean(), "pr_auc": cv["test_pr_auc"].mean(), "brier": -cv["test_brier"].mean(),
               "n": len(y), "events": int(y.sum()), "columns": X.shape[1]}
    text = "\n".join([
        f"Model: {model_type}; missing data: {missing_strategy}; {len(predictors)} predictors ({X.shape[1]} model columns).",
        f"Patients used: {len(y):,} of {len(df):,} ({int(y.sum())} events; {numbers['events'] / X.shape[1]:.1f} events per column).",
        f"5-fold cross-validation: AUC {cv['test_auc'].mean():.3f} ± {cv['test_auc'].std():.3f}, "
        f"PR-AUC {cv['test_pr_auc'].mean():.3f} ± {cv['test_pr_auc'].std():.3f} (a model with no skill scores {y.mean():.3f}), "
        f"Brier {-cv['test_brier'].mean():.3f} ± {cv['test_brier'].std():.3f}.",
        describe_drivers(model, X, y, model_type, missing_strategy),
    ])
    return text, numbers


@tool(parse_docstring=True)
@safe
def train_model(
    predictors: list[str],
    model_type: ModelType,
    missing_strategy: MissingStrategy,
) -> str:
    """Cross-validate a model that predicts heart failure and report AUC, PR-AUC, Brier score, patients used, and the main drivers.

    Uses 5-fold stratified cross-validation with a fixed seed, so the same call always gives the same answer. Drivers are adjusted odds ratios (logistic), the variables kept by the L1 penalty (penalized_logistic), or permutation importance on one test fold (random_forest, gradient_boosting).

    Args:
        predictors: Variable names to use as predictors.
        model_type: logistic (interpretable, needs enough events per predictor), penalized_logistic (L1 penalty; for many predictors), random_forest, or gradient_boosting.
        missing_strategy: complete_case drops patients with any missing predictor; impute fills in the median; native lets the model handle missing values (gradient_boosting only).
    """
    return train(predictors, model_type, missing_strategy)[0]


TOOLS = [list_variables, profile_data, compare_groups, train_model]


# ----------------------------------------------------------------------------------------------- final answer
class FinalModel(BaseModel):
    """The analyst's final answer, the same for every pattern so the runs can be compared."""
    model_type: ModelType
    missing_strategy: MissingStrategy
    predictors: list[str] = Field(description="Exact variable names, one per item; never a description of a group of variables")
    cv_auc: float = Field(description="Cross-validated AUC of this model as train_model reported it: one number such as 0.737 (0 if no model was trained)")
    pr_auc: float = Field(description="Cross-validated PR-AUC of this model as train_model reported it: one number such as 0.538 (0 if no model was trained)")
    key_drivers: list[str]
    rationale: str


def check_answer(final):
    """Re-run the chosen model ourselves and check the answer against simple rules."""
    text, numbers = train(final.predictors, final.model_type, final.missing_strategy)
    if numbers is None:
        return {"valid": False, "problem": text}
    return {
        "valid": True,
        "verified_auc": round(numbers["auc"], 3),
        "reported_auc_matches": abs(numbers["auc"] - final.cv_auc) <= 0.02,
        "admission_only": all(known_at(p) == "admission" for p in final.predictors),
        "no_variable_over_30pct_missing": all(pct_missing(p) <= 30 for p in final.predictors),
        "events_per_column_at_least_10": numbers["events"] / numbers["columns"] >= 10,
    }


# ----------------------------------------------------------------------------------------------- multi-agent team (module 3)
MCP_URL = "https://pubmed.caseyjhand.com/mcp"      # public PubMed MCP server (third-party; see the notebook for the caveats)


class Paper(BaseModel):
    pmid: int
    title: str
    year: int | None = None
    finding: str = Field(description="One sentence: what this paper found about risk factors for heart failure after MI")


class Literature(BaseModel):
    """What the Literature Scout found."""
    papers: list[Paper] = Field(description="Up to 5 relevant papers that were actually fetched")
    risk_factors: list[str] = Field(description="Risk factors for heart failure after MI that these papers name, as short phrases such as 'older age' or 'diabetes'")


class Review(BaseModel):
    """The Reviewer's decision on the analyst's answer."""
    verdict: Literal["accept", "revise"]
    issues: list[str] = Field(description="Specific problems to fix, one sentence each; empty if accepted")


@tool(parse_docstring=True)
@safe
def verify_answer(predictors: list[str], model_type: ModelType, missing_strategy: MissingStrategy, reported_auc: float) -> str:
    """Re-run the analyst's model and check it against our rules: predictors known at admission, at most 30% missing, at least 10 events per model column, and the reported AUC matches.

    Args:
        predictors: The predictor names the analyst used.
        model_type: The model type the analyst used.
        missing_strategy: The missing-data strategy the analyst used.
        reported_auc: The cross-validated AUC the analyst reported.
    """
    result = check_answer(SimpleNamespace(predictors=predictors, model_type=model_type, missing_strategy=missing_strategy, cv_auc=reported_auc))
    if not result["valid"]:
        return f"Could not re-run the model: {result['problem']}"
    late = [p for p in predictors if known_at(p) != "admission"]
    sparse = [f"{p} ({pct_missing(p):.0f}%)" for p in predictors if pct_missing(p) > 30]
    lines = [f"{'PASS' if result['reported_auc_matches'] else 'FAIL'}: reported AUC {reported_auc:.3f}, our re-run {result['verified_auc']:.3f} (must be within 0.02)",
             f"{'PASS' if result['admission_only'] else 'FAIL'}: every predictor is known at admission" + (f" (not at admission: {', '.join(late)})" if late else ""),
             f"{'PASS' if result['no_variable_over_30pct_missing'] else 'FAIL'}: no predictor has more than 30% missing values" + (f" (too sparse: {', '.join(sparse)})" if sparse else "")]
    numbers = train(predictors, model_type, missing_strategy)[1]
    lines.append(f"{'PASS' if result['events_per_column_at_least_10'] else 'FAIL'}: at least 10 events per model column ({numbers['events'] / numbers['columns']:.1f} here)")
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------------- model setup
def env(name):
    """An environment variable (from your shell or .env), with a clear message if it is missing."""
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"{name} is not set. Copy .env_example to .env, fill in the lines for your provider, and restart the kernel.")
    return value


def claude(model, **settings):
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(model=model or "claude-sonnet-5-5", max_tokens=4096, timeout=120, max_retries=2, **settings)
    if not (llm.profile or {}).get("structured_output"):
        # Old versions do not know new Claude models, so they ask for a forced tool call that the model rejects
        print(f"Note: langchain-anthropic {version('langchain-anthropic')} has no model profile for '{llm.model}'. This is harmless unless you see "
              "\"tool_choice ... not supported\"; then run: pip install -U langchain-anthropic anthropic, and restart the kernel.")
    return llm


def get_model(provider=None, model=None):
    """A LangChain chat model. PROVIDER, MODEL, and the keys come from your .env file (copy .env_example).
    Pass `provider` or `model` to override the file for one call."""
    load_dotenv(ROOT / ".env")                         # values already set in your shell win
    provider = provider or os.environ.get("PROVIDER") or "anthropic"
    model = model or os.environ.get("MODEL") or None
    if provider == "anthropic":                        # Claude, direct
        return claude(model, api_key=env("ANTHROPIC_API_KEY"))
    if provider == "openai":                           # OpenAI, direct
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or "gpt-5.6-terra", timeout=120, max_retries=2, api_key=env("OPENAI_API_KEY"))
    if provider == "foundry_claude":                   # Claude on Microsoft Foundry; `model` is your deployment name
        host = re.sub(r"^https?://", "", env("ANTHROPIC_FOUNDRY_RESOURCE")).split("/")[0]       # a resource name or a full URL
        host = host if "." in host else f"{host}.services.ai.azure.com"
        return claude(model, base_url=f"https://{host}/anthropic", api_key=env("ANTHROPIC_FOUNDRY_API_KEY"))
    if provider == "foundry_openai":                   # OpenAI models on Microsoft Foundry; `model` is your deployment name
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or "gpt-5.6-terra", timeout=120, max_retries=2, base_url=env("AZURE_OPENAI_BASE_URL"), api_key=env("AZURE_OPENAI_API_KEY"))
    raise ValueError(f"Unknown PROVIDER '{provider}'. Use anthropic, openai, foundry_claude, or foundry_openai.")


# ----------------------------------------------------------------------------------------------- run helpers
def where(metadata):
    """Which graph node a call belongs to, for example 'plan' or 'execute > model'."""
    path = (metadata or {}).get("langgraph_checkpoint_ns", "")
    return " > ".join(part.split(":")[0] for part in path.split("|") if part) or "model"


def estimate_cost(model, input_tokens, output_tokens):
    """Rough dollar cost of a run from litellm's price list (list prices; ignores discounts and caching).
    Returns None if litellm is not installed or does not know the model's price."""
    try:
        os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")    # use the price list shipped with litellm: no network call
        import litellm
        for name in (model, f"azure/{model}"):                          # Foundry deployments are often named like the model
            if name in litellm.model_cost:
                return sum(litellm.cost_per_token(model=name, prompt_tokens=input_tokens, completion_tokens=output_tokens))
    except Exception:
        pass
    return None


class RunStats(BaseCallbackHandler):
    """Counts model calls, tool calls, tokens, and time for one run, and records the trail: every model call
    (prompt and reply) and every tool call (arguments and result), in order. Pass it as config={"callbacks": [stats]}."""

    def __init__(self):
        self.llm_calls = self.tool_calls = self.tokens = self.input_tokens = self.output_tokens = 0
        self.model = None
        self.start = self.last = time.time()
        self.trail = []                       # every model call and tool call, in order
        self.pending = {}                     # calls that have started but not finished
        self.seen = set()                     # prompts already recorded: the system prompt repeats on every call

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self.llm_calls += 1
        self.model = self.model or (metadata or {}).get("ls_model_name")
        prompt = []
        for m in messages[0]:
            if m.type in ("system", "human") and (m.type, text_of(m)) not in self.seen:
                self.seen.add((m.type, text_of(m)))
                prompt.append({"role": m.type, "text": text_of(m)})
        self.pending[run_id] = {"kind": "model", "where": where(metadata), "prompt": prompt}

    def on_llm_end(self, response, *, run_id, **kwargs):
        message = response.generations[0][0].message
        usage = getattr(message, "usage_metadata", None) or {}
        self.tokens += usage.get("total_tokens", 0)
        self.input_tokens += usage.get("input_tokens", 0)
        self.output_tokens += usage.get("output_tokens", 0)
        if event := self.pending.pop(run_id, None):
            event["text"] = text_of(message)
            event["tool_calls"] = [{"name": c["name"], "args": c["args"]} for c in message.tool_calls if c["name"] != "FinalModel"]
            self.trail.append(event)
        self.last = time.time()

    def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, inputs=None, **kwargs):
        self.tool_calls += 1
        self.pending[run_id] = {"kind": "tool", "where": where(metadata), "tool": serialized["name"], "args": inputs or input_str}

    def on_tool_end(self, output, *, run_id, **kwargs):
        if event := self.pending.pop(run_id, None):
            content = getattr(output, "content", output)
            if isinstance(content, list):                  # MCP tools return a list of content blocks
                content = "\n".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
            event["result"] = str(content)
            self.trail.append(event)
        self.last = time.time()

    def on_tool_error(self, error, *, run_id, **kwargs):
        if event := self.pending.pop(run_id, None):
            event["result"] = f"ERROR: {error}"
            self.trail.append(event)

    def summary(self):
        return {"llm_calls": self.llm_calls, "tool_calls": self.tool_calls, "tokens": self.tokens,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "cost_usd": estimate_cost(self.model, self.input_tokens, self.output_tokens), "seconds": round(self.last - self.start)}


def text_of(message):
    return str(message.text).strip()


def show_trace(messages, width=300):
    """Print an agent's run: what it thought, which tool it called, and what came back."""
    for m in messages:
        if isinstance(m, AIMessage):
            if text_of(m):
                print(f"💭 {text_of(m)[:width]}")
            for call in m.tool_calls:
                if call["name"] != "FinalModel":              # the final answer is printed separately
                    args = ", ".join(f"{k}={v}" for k, v in call["args"].items())
                    print(f"🔧 {call['name']}({args[:width]})")
        elif isinstance(m, ToolMessage) and not text_of(m).startswith("Returning structured response"):
            print(f"   ↳ {text_of(m).replace(chr(10), ' | ')[:width]}")


def trace_text(messages, width=1500):
    """The tool calls and results of a run as text, so a critic can check the numbers."""
    parts = []
    for m in messages:
        if isinstance(m, AIMessage):
            parts += [f"CALL {c['name']}({c['args']})" for c in m.tool_calls if c["name"] != "FinalModel"]
        elif isinstance(m, ToolMessage) and not text_of(m).startswith("Returning structured response"):
            parts.append(f"RESULT {text_of(m)[:width]}")
    return "\n".join(parts)


def show_final(final):
    print(f"Model: {final.model_type} (missing data: {final.missing_strategy})")
    print(f"Predictors ({len(final.predictors)}): {', '.join(final.predictors)}")
    print(f"Cross-validated AUC {final.cv_auc:.3f} | PR-AUC {final.pr_auc:.3f}")
    print("Key drivers:\n  " + "\n  ".join(final.key_drivers))
    print(f"Rationale: {final.rationale}")


def show_cost(summary):
    cost = summary.get("cost_usd")
    price = "" if cost is None else f" (about ${cost:.2f})" if cost >= 0.01 else " (under $0.01)"
    print(f"Cost of this run: {summary['llm_calls']} model calls, {summary['tool_calls']} tool calls, {summary['tokens']:,} tokens{price}, {summary['seconds']} s")


def show_run(messages, final, summary):
    show_trace(messages)
    print()
    show_final(final)
    print()
    show_cost(summary)


RUNS = ROOT / "materials" / "runs"


def save_run(name, messages, final, summary, extra=None, trail=None):
    RUNS.mkdir(parents=True, exist_ok=True)
    data = {"messages": messages_to_dict(messages), "final": final.model_dump(), "summary": summary, "extra": extra, "trail": trail}
    (RUNS / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))
    export_trail(name)


def load_run(name):
    data = json.loads((RUNS / f"{name}.json").read_text())
    return messages_from_dict(data["messages"]), FinalModel(**data["final"]), data["summary"], data["extra"]


def run_or_replay(name, replay, run):
    """Run `run(stats)` live and save it, or load the saved run. `run` returns (messages, final, extra)."""
    if replay:
        return load_run(name)
    stats = RunStats()
    messages, final, extra = run(stats)
    summary = stats.summary()
    save_run(name, messages, final, summary, extra, stats.trail)
    return messages, final, summary, extra


async def arun_or_replay(name, replay, run):
    """Like run_or_replay, for async runs (MCP tools are async): `run(stats)` is a coroutine returning (messages, final, extra)."""
    if replay:
        return load_run(name)
    stats = RunStats()
    messages, final, extra = await run(stats)
    summary = stats.summary()
    save_run(name, messages, final, summary, extra, stats.trail)
    return messages, final, summary, extra


# ----------------------------------------------------------------------------------------------- the trail
def trail_from_messages(messages):
    """Rebuild a trail from an agent's messages (for runs saved before the trail was recorded)."""
    results = {m.tool_call_id: text_of(m) for m in messages if isinstance(m, ToolMessage)}
    trail, prompt = [], []
    for m in messages:
        if isinstance(m, HumanMessage):
            prompt.append({"role": "human", "text": text_of(m)})
        elif isinstance(m, AIMessage):
            calls = [c for c in m.tool_calls if c["name"] != "FinalModel"]
            trail.append({"kind": "model", "where": "model", "prompt": prompt, "text": text_of(m), "tool_calls": [{"name": c["name"], "args": c["args"]} for c in calls]})
            trail += [{"kind": "tool", "where": "tools", "tool": c["name"], "args": c["args"], "result": results.get(c["id"], "")} for c in calls]
            prompt = []
    return trail


def load_trail(name):
    data = json.loads((RUNS / f"{name}.json").read_text())
    return data.get("trail") or trail_from_messages(messages_from_dict(data["messages"]))


def show_trail(name, width=500):
    """Print every model call and tool call of a saved run, in order. Long texts are cut at `width` characters (None = no cut)."""
    def cut(text):
        return text if width is None or len(text) <= width else text[:width] + " ..."
    for i, event in enumerate(load_trail(name), 1):
        if event["kind"] == "model":
            print(f"\n[{i}] MODEL CALL ({event['where']})")
            for message in event["prompt"]:
                print(f"  💬 {message['role']}: {cut(message['text'])}")
            if event["text"]:
                print(f"  🤖 {cut(event['text'])}")
            for call in event["tool_calls"]:
                print(f"  🔧 calls {call['name']}({cut(str(call['args']))})")
        else:
            print(f"\n[{i}] TOOL RESULT: {event['tool']}")
            print(f"  ↳ {cut(event['result'])}")


def tools_by_agent(name):
    """The tool calls of each agent in a saved multi-agent run, for example {'scout': 'pubmed_search_articles → pubmed_fetch_articles'}."""
    sequences = {}
    for event in load_trail(name):
        if event["kind"] == "tool":
            agent = event["where"].split(" > ")[0]
            sequence = sequences.setdefault(agent, [])
            if sequence and sequence[-1][0] == event["tool"]:
                sequence[-1][1] += 1
            else:
                sequence.append([event["tool"], 1])
    return {agent: " → ".join(tool if count == 1 else f"{tool} ×{count}" for tool, count in sequence) for agent, sequence in sequences.items()}


def draw_graph(app):
    """Show a compiled LangGraph graph as a picture; if the drawing service is unreachable, print its Mermaid text instead."""
    from IPython.display import Image, display
    try:
        display(Image(app.get_graph().draw_mermaid_png()))
    except Exception:
        print(app.get_graph().draw_mermaid())


def tool_sequence(name):
    """The order of tool calls in a run, for example 'list_variables → compare_groups ×6 → train_model ×3'."""
    sequence = []
    for event in load_trail(name):
        if event["kind"] == "tool":
            if sequence and sequence[-1][0] == event["tool"]:
                sequence[-1][1] += 1
            else:
                sequence.append([event["tool"], 1])
    return " → ".join(tool if count == 1 else f"{tool} ×{count}" for tool, count in sequence)


def export_trail(name):
    """Write the complete trail (nothing cut) to materials/runs/<name>_trace.md."""
    lines = [f"# Trail of the '{name}' run", "", "Every model call and tool call in order. A prompt that repeats word for word (such as the system prompt) is shown only the first time.", ""]
    for i, event in enumerate(load_trail(name), 1):
        if event["kind"] == "model":
            lines += [f"## {i}. Model call ({event['where']})", ""]
            lines += [f"**{m['role']} message**\n\n````\n{m['text']}\n````\n" for m in event["prompt"]]
            if event["text"]:
                lines += [f"**Reply**\n\n````\n{event['text']}\n````\n"]
            lines += [f"**Calls tool** `{c['name']}` with `{c['args']}`\n" for c in event["tool_calls"]]
        else:
            lines += [f"## {i}. Tool result: {event['tool']}", "", f"Arguments: `{event['args']}`", "", f"````\n{event['result']}\n````", ""]
    (RUNS / f"{name}_trace.md").write_text("\n".join(lines))
