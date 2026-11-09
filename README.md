# Building AI Agents for Biomedical Research

Hands-on notebooks for the **BIOINFO GIW ISCB-Asia 2026 workshop**. 

| Session | Notebook | What you build | Needs |
|---|---|---|---|
| **2a** | `01_gui_agent_builders.ipynb` | A research team in **n8n** (no code): a Literature Scout, a human review step, a Data Analyst, and a report. Also the same team using an existing **MCP** server | n8n (Docker or the n8n Cloud trial) and an LLM key |
| **2b** | `02_agent_design_patterns.ipynb` | One Data Analyst agent in Python with three control patterns: **ReAct**, **Plan-and-Execute / SRPA**, and **Reflection**. Compares them on quality and cost | Python and an LLM key |
| **2c** | `03_multi_agent_langgraph.ipynb` | A **multi-agent workflow in LangGraph**: Scout, Analyst and Reviewer, wired as a straight line and then with a review loop | Python and an LLM key (plus internet for the PubMed MCP server) |

Do them in order. Each one reuses the data and the question from the one before.

## Quick start (sessions 2b and 2c)
1. **Python 3.10 or newer.** Install the packages:
   ```bash
   pip install -r requirements.txt
   ```
2. **Choose a model provider and add your key.** Copy the example file and fill in only the lines for your provider:
   ```bash
   cp .env_example .env        # Windows: copy .env_example .env
   ```
   Providers: Anthropic, OpenAI, or either one through Microsoft Foundry (Azure). Step-by-step guides are in `Instructions/`. **Never commit `.env`** (it is already in `.gitignore`).
3. Open the notebook in VS Code or Jupyter, pick the Python environment you installed into, and run the cells from the top. **Restart the kernel after changing `.env`.**

**No key, or the network is slow?** Set `REPLAY = True` in the first code cell of notebook 2 or 3. The notebook then shows the runs saved in `materials/runs/` and makes no model calls. (A live run of a notebook costs from a few cents to well under a dollar at list prices, and each run prints an estimate.)

For session 2a, follow the "Get n8n running" section inside `01_gui_agent_builders.ipynb`. You can also import the ready-made workflows in `workflows/` into n8n (`mi_research_team.json` builds the tools by hand, `mi_research_team_mcp.json` uses the PubMed MCP server). You then add your own model credential.

## What is in this folder
| Path | What it is |
|---|---|
| `01_…`, `02_…`, `03_…` `.ipynb` | The three notebooks |
| `mi_tools.py` | Shared code for sessions 2b and 2c: the four analysis tools, model setup, run and cost helpers. Open it to see how the tools work |
| `Data/` | The dataset (`mi_heart_failure.csv`) and its data dictionary (`dict_heart_failure.json`) |
| `materials/` | Prompts and templates used by the n8n workflow, and `runs/` with saved agent runs (for `REPLAY = True`) |
| `workflows/` | Importable n8n workflows |
| `Instructions/` | How to get API keys (Anthropic, OpenAI, Microsoft Foundry) |
| `.env_example` | Template for your private `.env` |

## The data
1,700 patients admitted with acute MI to one hospital in Krasnoyarsk, Russia (1992–1995), from the [UCI Machine Learning Repository, "Myocardial infarction complications" (ID 579)](https://archive.ics.uci.edu/dataset/579/myocardial+infarction+complications). We kept one outcome, in-hospital heart failure (394 patients, 23.2%), and gave the columns readable names. `Data/dict_heart_failure.json` lists every variable with its original name, codes, and when it is known (at admission or later). Check the UCI page for the dataset's terms of use.

## Good to know
- **This is a teaching project, not clinical software.** The models are small examples on one historical dataset and must not be used for patient care.
- **Agents are not deterministic.** They choose their own tool calls, so your run will differ from the saved ones. The notebooks say what to look at rather than what to expect.
- **The PubMed MCP server** used in sessions 2a and 2c (`pubmed.caseyjhand.com`) is a public third-party service run by an individual, not by NCBI. It can change or go down, and your queries go to it. `REPLAY = True` avoids it.
- Notebooks 2b and 2c end with a **Troubleshooting** table for the errors we hit most often (old `langchain-anthropic`, stale kernel, MCP and `await` errors).

## Questions
If you have any further questions, please reach out to either **Attri Ghosh** ([attri.ghosh@cshs.org](mailto:attri.ghosh@cshs.org)) or **Philip Freda** ([philip.freda@csmc.edu](mailto:philip.freda@csmc.edu)).
