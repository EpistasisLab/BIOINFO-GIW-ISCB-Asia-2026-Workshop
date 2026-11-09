# Using Claude and OpenAI Models through Microsoft Foundry (Azure)

**Building AI Agents for Biomedical Research** · ISCB-ASIA 2026 Workshop

---

## When to use this guide

Use this guide if your institution gives you access to Microsoft Azure and you want to run the workshop's Anthropic (Claude) and OpenAI models through **Microsoft Foundry** (Azure's AI platform, formerly Azure AI Foundry) instead of getting keys directly from Anthropic or OpenAI.

If you are getting keys directly from the providers, use `anthropic_api_key_setup.md` and `openai_api_key_setup.md` instead. You only need one route.

### How Foundry differs from getting keys directly

| | Direct from Anthropic / OpenAI | Microsoft Foundry |
|---|---|---|
| Account | Claude Console or OpenAI API Platform | An Azure subscription |
| Billing | Prepaid credits with each provider | Your Azure bill (Claude through the Azure Marketplace) |
| Models | All models available with one key | **Each model must be deployed** before you can use it |
| In code, `model=` is | The model name | **Your deployment name** |
| Endpoint | The provider's standard endpoint | Your own resource's endpoint URL |

The most important difference: **on Foundry, you deploy each model separately.** That is why the workshop recommends deploying several model sizes ahead of time.

---

## Before you start

You need:

- **An Azure subscription** that allows Azure Marketplace purchases. Claude in Foundry is billed through the Azure Marketplace, and some free, student, or sponsored subscriptions can't buy Marketplace offers. If you use an institutional subscription, check with your IT or cloud team first.
- **Access to the [Foundry portal](https://ai.azure.com)**.
- **A role on the resource that lets you use it**, such as *Foundry User* (formerly *Azure AI User*) or *Cognitive Services User*. If you create the resource yourself, you normally have this already.

> **Start at least a week before the workshop.** Institutional approvals, Marketplace terms, and quota requests can take time.

---

## Step 1 — Create a Foundry resource

A **resource** holds your security and billing settings. **Deployments** (the model instances you call from code) live inside it. One resource can hold both your Claude and OpenAI deployments.

1. Go to the [Foundry portal](https://ai.azure.com) and sign in with your Azure account.
2. Create a new Foundry resource (or a Foundry project, which creates a resource for you), or select an existing one your institution provides.
3. **Note the resource name.** You will use it in your endpoint URLs, for example `my-iscb-resource`.

## Step 2 — Deploy the Claude models

1. In the Foundry portal, select **Discover**, then **Models**, to open the model catalog.
2. Search for a Claude model, for example `claude-haiku-5-5`, and select it.
3. Select **Deploy**, then **Custom settings**.
4. **On your first Claude deployment only:** review the Azure Marketplace terms, select an industry, and select **Agree and Proceed**.
5. Configure the deployment:
   - **Deployment name:** keep the default (it matches the model name), so the workshop code works without changes.
   - **Region scope:** select **Global**.
   - **Model version (hosting option):** choose **Hosted on Azure** or **Hosted on Anthropic**. See the note below.
6. Select **Deploy** and wait for it to finish.
7. Repeat for the other two sizes:

| Model | Deployment name to use |
|---|---|
| Claude Haiku | `claude-haiku-5-5` |
| Claude Sonnet | `claude-sonnet-5-5` |
| Claude Opus | `claude-opus-5-5` |

> **Which hosting option?** *Hosted on Azure* keeps your prompts and responses within Azure and suits most uses. 

## Step 3 — Deploy the OpenAI models

1. In the same model catalog, search for the OpenAI models, for example **GPT-5.6 Luna, Terra, and Sol**. If these are not listed for your region or subscription yet, choose the closest current equivalents.
2. Select a model, then **Deploy**, and keep the default deployment name.
3. Repeat for each size:

| Model | Deployment name to use |
|---|---|
| GPT-5.6 Luna | `gpt-5.6-luna` |
| GPT-5.6 Terra | `gpt-5.6-terra` |
| GPT-5.6 Sol | `gpt-5.6-sol` |

If you choose different deployment names, write them down. You'll need to use them in place of the model names in the workshop code.

## Step 4 — Copy your endpoint and key

1. In the Foundry portal, select **Build**, then **Models**, and open one of your deployments.
2. On the **Details** tab, copy the **Target URI** (your endpoint) and the **Key**.

Your two endpoints follow these patterns, with your own resource name:

| Provider | Endpoint (base URL) |
|---|---|
| Claude | `https://<your-resource>.services.ai.azure.com/anthropic/` |
| OpenAI | `https://<your-resource>.openai.azure.com/openai/v1/` |

> If you use the classic Foundry portal layout, find your deployments and their keys under **Models + endpoints** (in **My assets**) instead.

## Step 5 — Store your settings safely

Put these in a `.env` file in the workshop folder (or set them as environment variables), and make sure `.env` is listed in your `.gitignore`:

```
# Claude through Foundry (variable names read automatically by the Anthropic SDK)
ANTHROPIC_FOUNDRY_API_KEY=<your key>
ANTHROPIC_FOUNDRY_RESOURCE=<your-resource>

# OpenAI through Foundry
AZURE_OPENAI_API_KEY=<your key>
AZURE_OPENAI_BASE_URL=https://<your-resource>.openai.azure.com/openai/v1/
```

> **Never commit keys to GitHub.** Anyone with your key can run models on your Azure bill. If a key is exposed, regenerate it in the Azure portal.

## Step 6 — Test both providers

Install the SDKs:

```bash
pip install -U anthropic openai python-dotenv
```

**Test Claude:**

```python
from dotenv import load_dotenv
from anthropic import AnthropicFoundry

load_dotenv()
client = AnthropicFoundry()  # reads ANTHROPIC_FOUNDRY_API_KEY and ANTHROPIC_FOUNDRY_RESOURCE

reply = client.messages.create(
    model="claude-haiku-5-5",  # your deployment name
    max_tokens=50,
    messages=[{"role": "user", "content": "Say hello to the ISCB-ASIA workshop."}],
)
print(reply.content[0].text)
```

**Test OpenAI:**

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
)

reply = client.responses.create(
    model="gpt-5.6-luna",  # your deployment name
    input="Say hello to the ISCB-ASIA workshop.",
)
print(reply.output_text)
```

**If both print a greeting, you're ready.** After this setup, the workshop code works the same way as with direct keys; only the client setup and the `model=` names (your deployment names) differ.

---

## Switching between model sizes

Once all three sizes are deployed, switching is a one-word change, just as with direct keys. The only difference is that you pass deployment names:

```python
from anthropic import AnthropicFoundry

client = AnthropicFoundry()
question = "In two sentences, what is cardiogenic shock?"

for deployment in ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]:
    reply = client.messages.create(
        model=deployment,
        max_tokens=150,
        messages=[{"role": "user", "content": question}],
    )
    print(f"--- {deployment}\n{reply.content[0].text}\n")
```

Note that the "list available models" call from the direct-key guides does not work for Claude on Foundry. Check your deployments in the Foundry portal under **Build → Models** instead.

---

## Billing and cost control

- **Claude** is billed through the Azure Marketplace in Claude Consumption Units, metered hourly and charged monthly on your Azure bill. There are no prepaid credits.
- **OpenAI models** are billed as regular Azure usage on the same bill.
- **Set a budget alert** in Azure Cost Management before the workshop, so you're notified if spending exceeds what you expect. The workshop exercises use only a small amount of usage.

---

## Troubleshooting

| Error | What it means | Fix |
|---|---|---|
| 401 Unauthorized / invalid key | The key is wrong or the environment variable isn't set | Re-copy the key from the deployment's **Details** tab; restart your terminal or IDE |
| 403 Forbidden | Your account doesn't have permission on the resource | Ask your admin for the *Foundry User* or *Cognitive Services User* role |
| Deployment not found / model not found | The `model=` value doesn't match a deployment | Use your exact deployment name; check it under **Build → Models** |
| 400 Bad Request when using skills, code execution, or files | The Claude deployment is hosted on Azure, which doesn't support these features | Create a deployment with the *Hosted on Anthropic* option |
| 429 Too Many Requests | You hit your deployment's rate limit | Wait a few seconds and retry; request a quota increase in the Azure portal if it keeps happening |
| Can't accept the Marketplace terms | Your subscription doesn't allow Marketplace purchases | Contact your IT or cloud team, or use direct keys instead |

---

## Further reading

- [Claude in Microsoft Foundry (Anthropic docs)](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry)
- [Azure OpenAI v1 API (Microsoft Learn)](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)
- [Foundry model catalog: Anthropic models](https://ai.azure.com/catalog/publishers/anthropic)
