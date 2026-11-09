# Getting an OpenAI API Key

**Building AI Agents for Biomedical Research** · ISCB-ASIA 2026 Workshop

---

## An API key is not the same as a ChatGPT account

If you use ChatGPT at [chatgpt.com](https://chatgpt.com), whether on a free or paid plan (Plus, Pro, Team), that account does **not** give you an API key.

ChatGPT and the OpenAI API Platform are separate products:

- **ChatGPT plans** are for using ChatGPT in the web, desktop, and mobile apps.
- **The OpenAI API Platform** is OpenAI's developer platform. It provides the API keys you need to call OpenAI models from your own code.

The agents in this workshop call OpenAI models from Python, so you need **API Platform access**. API usage is billed separately, and paying for ChatGPT Plus or Pro does not give you any API credits.

---

## Step 1 — Check that your country is supported

The API is only available in certain countries and regions. Check OpenAI's [supported countries list](https://developers.openai.com/api/docs/supported-countries) before you start. Using a VPN does not make an unsupported location eligible.

## Step 2 — Open the API Platform and sign in

Go to [platform.openai.com](https://platform.openai.com) and sign in or create an account. You can use the same login as ChatGPT, but billing and usage are completely separate.

## Step 3 — Add credits

New API accounts use **prepaid credits**, which you buy in the **Billing** section of your settings.

- **A key without credits will not work.** Creating a key and buying credits are separate steps.
- The minimum purchase is small (USD 5).
- Purchased credits expire after one year.
- If you turn on auto-recharge, set a sensible limit, or turn it off after the workshop.

## Step 4 — Create a key

1. Choose the **project** that will own the key (the default project is fine). Projects help you keep workshop usage separate from other work.
2. Open the [API Keys page](https://platform.openai.com/api-keys).
3. Create a new secret key and give it a name like `iscb-workshop`, so you can find and delete it afterwards.
4. Keep the permissions at **All** for the workshop. (Restricted keys can limit which endpoints a key may use, which is useful for production but not needed here.)

## Step 5 — Copy and store the key safely

Copy the key right away. **It is shown only once**; if you lose it, create a new one. OpenAI keys start with `sk-`.

Store it as an environment variable rather than pasting it into notebooks:

```bash
# macOS / Linux (add this line to ~/.zshrc or ~/.bashrc to make it permanent)
export OPENAI_API_KEY="sk-..."
```

```powershell
# Windows (PowerShell)
setx OPENAI_API_KEY "sk-..."
```

Alternatively, put it in a `.env` file in the workshop folder, alongside your Anthropic key:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Make sure `.env` is listed in your `.gitignore`.

> **Never commit API keys to GitHub.** If a key is ever exposed, delete it on the API Keys page and create a new one.

## Step 6 — Test the key

```python
# pip install openai
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY from the environment
reply = client.responses.create(
    model="gpt-5.6-luna",
    input="Say hello to the ISCB-ASIA workshop.",
)
print(reply.output_text)
```

**If it prints a greeting, you're ready.** You can also check the [Usage page](https://platform.openai.com/usage) to confirm the request was recorded under the right project.

| Error | What it means | Fix |
|---|---|---|
| Authentication error (401) | The key wasn't copied correctly, or the environment variable isn't set | Re-copy the key; restart your terminal or IDE after setting the variable |
| Insufficient quota (429) | The account has no credits | Add credits in Billing (Step 3) |
| Model not found, or a verification message | Your project can't use that model yet | Try another model from the list below; if asked to verify your organization, follow the link in the error |

---

## One key, every model: no deployment needed

With a key from the OpenAI API Platform, you **don't deploy models**. A single key gives you access to all the current models, and you choose which one to use in each request by changing the `model` name.

| Model | Model name in code | Use it for |
|---|---|---|
| GPT-5.6 Luna | `gpt-5.6-luna` | Fast, low-cost tasks: routing, extraction, simple tool calls |
| GPT-5.6 Terra | `gpt-5.6-terra` | Everyday agent work: analysis, multi-step tool use |
| GPT-5.6 Sol | `gpt-5.6-sol` | The hardest reasoning: planning, critiquing, complex analyses |

Switching models is a one-word change:

```python
from openai import OpenAI

client = OpenAI()
question = "In two sentences, what is cardiogenic shock?"

for model in ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]:
    reply = client.responses.create(model=model, input=question)
    print(f"--- {model}\n{reply.output_text}\n")
```

Model names change as new versions are released. To see the models your key can use right now:

```python
for m in client.models.list():
    print(m.id)
```

**A note on rate limits.** New accounts start on a low usage tier, which limits how many requests you can send per minute. The limits rise automatically as your account spends more over time. The starting tier is enough for the workshop, but if you see occasional rate-limit errors, wait a few seconds and retry.

---

