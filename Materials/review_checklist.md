# Review checklist: the Data Analyst's answer

A good answer:
- Calls `lookup_variable` for each risk factor and variable it discusses (check the Logs), and quotes numbers that match the data profile exactly. For example, diabetes: HF 36.8% if yes vs 21.2% if no (p<0.001).
- Leaves out or flags the variables with more than 30% missing data: family_history_coronary_disease, systolic_bp_emergency_team, diastolic_bp_emergency_team, serum_cpk, opioids_emergency_team, nsaids_emergency_team, lidocaine_emergency_team.
- Uses only variables known at admission for a prediction made at admission. Known only later: pain_relapse_day_1, pain_relapse_day_2, pain_relapse_day_3, opioids_icu_day_1, opioids_icu_day_2, opioids_icu_day_3, nsaids_icu_day_1, nsaids_icu_day_2, nsaids_icu_day_3.
- Flags prior_heart_failure (heart failure before this MI): HF by code: 0: 18.7%, 1: 87.4%, 2: 22.2% (n=27), 3: 31.0% (n=29), 4: 31.6% (n=19) (p<0.001). A model that uses it may mostly detect heart failure the patient already had.
- Flags cardiogenic_shock_at_admission as a likely competing risk (these patients often die before heart failure can develop): HF 2.2% if yes vs 23.8% if no (p<0.001).
- Says which literature risk factors are not in our dataset, such as ejection fraction, natriuretic peptides (BNP), troponin, kidney function, or modern treatments such as PCI and SGLT2 inhibitors.
- Notes that heart_failure is recorded during the hospital stay only, with no follow-up after discharge.
- Proposes predictive questions with a clear outcome, predictors, and method, and does not claim results that nobody has computed.
