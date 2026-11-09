# Getting an Anthropic (Claude) API Key

**Building AI Agents for Biomedical Research** · ISCB-ASIA 2026 Workshop

---

## An API key is not the same as a Claude.ai account

If you chat with Claude at [claude.ai](https://claude.ai), whether on a free or paid plan, that account does **not** give you an API key.

Claude.ai and the Claude Console are separate products:

- **Claude.ai plans** are for using Claude in the web, desktop, and mobile apps.
- **The Claude Console** is Anthropic's developer platform. It provides the API keys you need to call Claude from your own code.

The agents in this workshop call Claude from Python, so you need **Console access**. API usage is billed separately from any Claude.ai subscription. (Some Max and Team plans include monthly API credits, but you still need to set up Console access to use them.)

---

## Step 1 — Open the Claude Console

Go to [platform.claude.com](https://platform.claude.com). The older address, console.anthropic.com, redirects to the same place.

## Step 2 — Create an account or sign in

Sign up with your email address or a Google account.

## Step 3 — Add credits

Most self-serve accounts use **prepaid credits**, which you buy on the **Billing** page.

- Creating a key and buying credits are separate steps. **A key without credits will not work.**
- A small amount of credit is enough for the workshop.
- Consider setting a spending limit so you can't be surprised by charges.

## Step 4 — Create a key

1. Click **API Keys** in the left sidebar.
2. Create a new key.
3. Give it a name and choose a workspace. Use a name like `iscb-workshop` so you can find and delete it after the workshop.
4. Generate the key.

## Step 5 — Copy and store the key safely

Copy the key right away, since it may not be shown again. A valid key starts with `sk-ant-`.

Store it as an environment variable rather than pasting it into notebooks:

```bash
# macOS / Linux (add this line to ~/.zshrc or ~/.bashrc to make it permanent)
export ANTHROPIC_API_KEY="sk-ant-..."
```

```powershell
# Windows (PowerShell)
setx ANTHROPIC_API_KEY "sk-ant-..."
```

Alternatively, put it in a `.env` file in the workshop folder:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Make sure `.env` is listed in your `.gitignore`.

> **Never commit API keys to GitHub.** If a key is ever exposed, delete it in the Console and create a new one.

## Step 6 — Test the key

```python
# pip install anthropic
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
reply = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say hello to the ISCB-ASIA workshop."}],
)
print(reply.content[0].text)
```

**If it prints a greeting, you're ready.**

| Error | What it means | Fix |
|---|---|---|
| Authentication error | The key wasn't copied correctly, or the environment variable isn't set | Re-copy the key; restart your terminal or IDE after setting the variable |
| Billing or credit error | The account has no credits | Add credits on the Billing page (Step 3) |

---

## One key, every model: no deployment needed

With a key from the Claude Console, you **don't deploy models**. A single key gives you access to all the current Claude models, and you choose which one to use in each request by changing the `model` name.

| Model | Model name in code | Use it for |
|---|---|---|
| Claude Haiku | `claude-haiku-5-5` | Fast, low-cost tasks: routing, extraction, simple tool calls |
| Claude Sonnet | `claude-sonnet-5-5` | Most agent work: analysis, multi-step tool use |
| Claude Opus | `claude-opus-5-5` | The hardest reasoning: planning, critiquing, complex analyses |

Switching models is a one-word change:

```python
import anthropic

client = anthropic.Anthropic()
question = "In two sentences, what is cardiogenic shock?"

for model in ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]:
    reply = client.messages.create(
        model=model,
        max_tokens=150,
        messages=[{"role": "user", "content": question}],
    )
    print(f"--- {model}\n{reply.content[0].text}\n")
```


Model names change as new versions are released. To see the models your key can use right now:

```python
for m in client.models.list():
    print(m.id)
```

---

