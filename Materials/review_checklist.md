# Review checklist: the Data Analyst's answer

A good answer:
- Looks up each risk factor and variable it discusses with `lookup_variable` (check the Logs; one call can list several keywords), and quotes numbers that match the data profile (training set) exactly. For example, diabetes: HF 39.7% if yes vs 20.9% if no (p<0.001).
- Leaves out or flags the variables with more than 30% missing data: family_history_coronary_disease, systolic_bp_emergency_team, diastolic_bp_emergency_team, serum_cpk, opioids_emergency_team, nsaids_emergency_team, lidocaine_emergency_team.
- Uses only variables known at admission for a prediction made at admission. Known only later: pain_relapse_day_1, pain_relapse_day_2, pain_relapse_day_3, opioids_icu_day_1, opioids_icu_day_2, opioids_icu_day_3, nsaids_icu_day_1, nsaids_icu_day_2, nsaids_icu_day_3.
- Flags prior_heart_failure (heart failure before this MI): HF by code: 0: 18.4%, 1: 90.4%, 2: 28.6% (n=21), 3: 36.4% (n=22), 4: 30.8% (n=13) (p<0.001). A model that uses it may mostly detect heart failure the patient already had.
- Flags cardiogenic_shock_at_admission as a likely competing risk (these patients often die before heart failure can develop): HF 0.0% if yes vs 23.8% if no (p=0.002).
- Says which literature risk factors are not in our dataset, such as ejection fraction, natriuretic peptides (BNP), troponin, kidney function, or modern treatments such as PCI and SGLT2 inhibitors.
- Notes that heart_failure is recorded during the hospital stay only, with no follow-up after discharge.
- Proposes predictive questions with a clear outcome, predictors, and method, and does not claim results that nobody has computed.
- Ends with a `features` list of exact variable names that it looked up, all known at admission and with at most 30% missing. (The model step drops anything else and says so.)
- Says which feature set it chose and why, and quotes no model results: it never sees them.
