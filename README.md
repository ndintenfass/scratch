# Declarative Agent Framework

Define an agent in a YAML file. POST it to the API. Get a live, conversational agent accessible via HTTP with a built-in web UI.

The first agent type is an **Interview Bot** — configurable structured-discovery conversations that collect a rich set of user metadata while staying natural and on-topic.

---

## ⚡ Deploy to Render (5 minutes)

### 1. Get your Anthropic API key

Sign up at [console.anthropic.com](https://console.anthropic.com/) and create an API key.

### 2. Fork this repository

Fork `ndintenfass/scratch` to your own GitHub account so Render can connect to it.

### 3. Create a new Web Service on Render

1. Go to [dashboard.render.com](https://dashboard.render.com/) → **New → Web Service**
2. Connect your GitHub account and select your fork
3. Render will detect `render.yaml` automatically — the service is pre-configured

### 4. Set your API key

In the Render service settings → **Environment** tab:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your key from step 1) |

The other env vars (`ADMIN_CONFIG_PATH`, `DEFAULT_LLM_CLOUD`) are already set in `render.yaml`.

### 5. Deploy

Click **Deploy**. Render will:
- Install Python 3.11 and dependencies
- Start the server with `uvicorn`
- Health-check at `/health`

The first deploy takes ~2 minutes. Subsequent deploys are faster.

### 6. Open the web UI

Visit `https://your-service.onrender.com/ui` — you'll see the Dashboard with your configured LLM clouds. Click **Create Agent**, hit **Deploy Agent**, then **Open Chat** to start a conversation.

> **Tip:** The default cloud on Render is `anthropic-claude-sonnet`. To use the cheaper/faster Haiku model, change `DEFAULT_LLM_CLOUD` to `anthropic-claude-haiku` in the Render environment tab and redeploy.

---

## 🖥️ Run Locally

### Option A — Ollama (recommended; no API key needed)

```bash
# 1. Install Ollama from https://ollama.com/ and pull a model
ollama pull llama3.2

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload

# 4. Open http://localhost:8000 — redirects to the web UI
```

`admin_config.yaml` defaults to `ollama-llama3`, so no configuration is needed.

### Option B — Anthropic API (cloud model locally)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export DEFAULT_LLM_CLOUD=anthropic-claude-sonnet

pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 🌐 Web UI

Open `/ui` (or `/` which redirects there) after starting the server.

### Dashboard tab
- **Server status** — live health indicator
- **LLM Clouds** — all clouds from `admin_config.yaml`, active default highlighted
- **Deployed Agents** — list of live agents; click any row to open it in Chat

### Create Agent tab
- YAML textarea pre-filled with the example Customer Discovery Bot spec
- Edit the YAML to define your own agent (change name, fields, tone, triggers…)
- Click **Deploy Agent** — the agent goes live immediately
- Click **Open Chat** to start talking to it

### Chat tab
- Full conversation interface
- **Collected Metadata** panel (right side) updates in real-time as the agent extracts structured data
- Customer segment badge appears once detected
- Conversation auto-closes when all required fields are collected

---

## 📡 API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Redirect to `/ui` |
| `GET` | `/health` | Liveness check |
| `GET` | `/admin/config` | Loaded LLM cloud registry + active default |
| `GET` | `/agents` | List all deployed agents |
| `POST` | `/agents` | Create agent from inline spec `{ "spec": {...} }` |
| `POST` | `/agents/from-package` | Create from package dir `{ "package_path": "..." }` |
| `GET` | `/agents/{agent_id}` | Describe an agent |
| `DELETE` | `/agents/{agent_id}` | Deactivate an agent |
| `POST` | `/agents/{agent_id}/conversations` | Submit message → retrieval token |
| `GET` | `/agents/{agent_id}/conversations/{token}` | Poll for result |

Interactive docs at `/docs` (Swagger) and `/redoc`.

### Async token pattern

```python
import time, requests

BASE = "https://your-service.onrender.com"
AGENT_ID = "agent_abc123"

# Submit a message — returns immediately
resp = requests.post(f"{BASE}/agents/{AGENT_ID}/conversations", json={
    "message": "Hi! I run a 20-person SaaS startup and we're struggling with onboarding."
})
token     = resp.json()["token"]
conv_id   = resp.json()["conversation_id"]

# Poll until complete
while True:
    result = requests.get(f"{BASE}/agents/{AGENT_ID}/conversations/{token}").json()
    if result["status"] == "complete":
        print("Agent:", result["agent_response"])
        print("Metadata:", result["collected_metadata"])
        break
    time.sleep(0.5)

# Continue the conversation
resp = requests.post(f"{BASE}/agents/{AGENT_ID}/conversations", json={
    "message": "We use Notion and email — it's a mess.",
    "conversation_id": conv_id,
})
```

---

## 🗂️ Agent Packages

An agent **package** is a directory (or git repo) with an `agent.yaml` file:

```
my-discovery-bot/
├── agent.yaml    ← required: the declarative spec
└── README.md     ← optional: description
```

Deploy from a package directory:
```bash
curl -X POST http://localhost:8000/agents/from-package \
  -H "Content-Type: application/json" \
  -d '{"package_path": "./examples/interview_bot"}'
```

The example package is at [`examples/interview_bot/`](examples/interview_bot/).

---

## ⚙️ Admin Config (`admin_config.yaml`)

Defines available LLM clouds. Each agent spec references a cloud by name.

```yaml
llm_clouds:
  # Local — no API key
  ollama-llama3:
    provider: ollama
    model: llama3.2
    base_url: "http://localhost:11434"

  # Cloud — requires ANTHROPIC_API_KEY
  anthropic-claude-sonnet:
    provider: anthropic
    model: claude-sonnet-4-6
    proxy_endpoint: "http://llm-proxy.internal/v1"   # future production proxy
    api_key_env: ANTHROPIC_API_KEY
    use_proxy: false   # false = direct API; true = route through proxy_endpoint

defaults:
  llm_cloud: ollama-llama3   # override with DEFAULT_LLM_CLOUD env var
```

**`DEFAULT_LLM_CLOUD` env var** overrides `defaults.llm_cloud` without editing the YAML — this is how `render.yaml` switches the deployment to Anthropic while keeping local dev on Ollama.

---

## 🏗️ Architecture

```
admin_config.yaml               ← LLM cloud registry
examples/interview_bot/
  agent.yaml                    ← example agent package spec
  README.md

app/
  main.py                       ← FastAPI app + lifespan startup
  config.py                     ← loads admin_config, applies DEFAULT_LLM_CLOUD
  store.py                      ← in-memory store (swap for Redis/Postgres in production)
  static/
    index.html                  ← single-page web UI
  models/
    admin.py                    ← AdminConfig, LLMCloudConfig
    spec.py                     ← AgentSpec, InterviewBotConfig, MetadataField …
    api.py                      ← API request/response models
  llm/
    base.py                     ← BaseLLMProxy interface  ← REAL PROXY PLUGS IN HERE
    mock.py                     ← stub for unit tests
    ollama_proxy.py             ← local Ollama
    anthropic_proxy.py          ← Anthropic API (direct or via proxy_endpoint)
  agents/
    base.py                     ← BaseAgent + ConversationState
    factory.py                  ← AgentFactory (spec + admin config → live agent)
    interview_bot.py            ← InterviewBotAgent conversation engine
    extraction/
      json_block.py             ← LLM self-reports fields (default)
      second_pass.py            ← separate extraction LLM call
      heuristic.py              ← regex/keyword matching
  routers/
    agents.py                   ← /agents routes
    admin.py                    ← /admin/config route

render.yaml                     ← Render.com deployment blueprint
requirements.txt
```

### Key design seams

**LLM proxy swap point:** `app/llm/base.py` defines `BaseLLMProxy`. In production a shared infrastructure proxy sits here — set `use_proxy: true` in the cloud config and point `proxy_endpoint` at it. No agent code changes needed.

**Conversation state:** Lives in-memory (`AgentStore`). Replace the store with a Redis/Postgres-backed implementation (same async interface) to persist across restarts.

**Agent packages:** A directory with `agent.yaml` is the unit of versioning and deployment — same file you run locally can be committed and deployed by pointing the framework at a repo clone.
