# Declarative Agent Framework — Prototype

A system that turns a YAML file into a live, API-accessible agent.

Define an agent declaratively → POST it to the API → get a running agent that
accepts messages, processes them asynchronously, and returns structured results.

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure an LLM

**Option A — Local Ollama (recommended for development, no API key needed):**

```bash
# Install Ollama from https://ollama.com/
ollama pull llama3.2

# Ensure admin_config.yaml has defaults.llm_cloud: ollama-llama3 (it does by default)
```

**Option B — Anthropic cloud:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Edit admin_config.yaml → defaults.llm_cloud: anthropic-claude-sonnet
```

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

Open the interactive API docs: http://localhost:8000/docs

---

## Creating an agent

### From a package directory (recommended)

An **agent package** is a directory containing an `agent.yaml` spec file.
This is the canonical way to version-control an agent definition in a git repo.

```bash
curl -X POST http://localhost:8000/agents/from-package \
  -H "Content-Type: application/json" \
  -d '{"package_path": "./examples/interview_bot"}'
```

### From an inline spec

```python
import yaml, requests

with open("examples/interview_bot/agent.yaml") as f:
    spec = yaml.safe_load(f)

resp = requests.post("http://localhost:8000/agents", json={"spec": spec})
agent_id = resp.json()["agent_id"]
print(f"Agent created: {agent_id}")
```

---

## Running a conversation

The API uses an **async token pattern**: submit a message → get a retrieval
token → poll until the result is ready.

```python
import time, requests

BASE = "http://localhost:8000"
AGENT_ID = "agent_abc123"  # from the create step

# --- Start a new conversation ---
resp = requests.post(f"{BASE}/agents/{AGENT_ID}/conversations", json={
    "message": "Hi! I manage a 15-person engineering team at a Series B startup."
})
token = resp.json()["token"]
conv_id = resp.json()["conversation_id"]

# --- Poll for result ---
while True:
    result = requests.get(f"{BASE}/agents/{AGENT_ID}/conversations/{token}").json()
    if result["status"] == "complete":
        print("Agent:", result["agent_response"])
        print("Collected:", result["collected_metadata"])
        break
    time.sleep(0.5)

# --- Continue the conversation ---
resp = requests.post(f"{BASE}/agents/{AGENT_ID}/conversations", json={
    "message": "We mostly struggle with our deployment pipeline and on-call rotation.",
    "conversation_id": conv_id,
})
token2 = resp.json()["token"]
# ... poll as above
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agents` | Create agent from inline spec |
| `POST` | `/agents/from-package` | Create agent from package directory |
| `GET` | `/agents/{agent_id}` | Describe an agent |
| `DELETE` | `/agents/{agent_id}` | Deactivate an agent |
| `POST` | `/agents/{agent_id}/conversations` | Submit a message, get token |
| `GET` | `/agents/{agent_id}/conversations/{token}` | Poll for result |
| `GET` | `/health` | Liveness check |

Full interactive docs available at `/docs` (Swagger) and `/redoc`.

---

## Architecture

```
admin_config.yaml               ← LLM cloud registry
examples/interview_bot/
  agent.yaml                    ← declarative agent spec (the "package")

app/
  main.py                       ← FastAPI app + lifespan startup
  config.py                     ← loads admin_config.yaml
  store.py                      ← in-memory store (agents, conversations, tokens)
  models/
    admin.py                    ← AdminConfig, LLMCloudConfig
    spec.py                     ← AgentSpec, InterviewBotConfig, MetadataField …
    api.py                      ← API request/response models
  llm/
    base.py                     ← BaseLLMProxy interface  ← THE REAL PROXY PLUGS IN HERE
    mock.py                     ← stub for unit tests
    ollama_proxy.py             ← local Ollama model
    anthropic_proxy.py          ← Anthropic API (direct or via proxy)
  agents/
    base.py                     ← BaseAgent + ConversationState
    factory.py                  ← AgentFactory (spec → live agent)
    interview_bot.py            ← InterviewBotAgent implementation
    extraction/
      __init__.py               ← ExtractionStrategy ABC + factory
      json_block.py             ← LLM self-reports field values (default)
      second_pass.py            ← separate extraction LLM call
      heuristic.py              ← regex/keyword matching
  routers/
    agents.py                   ← all /agents routes
```

### Key design seams

**LLM proxy swap point:** `app/llm/base.py` defines `BaseLLMProxy`. In
production, `AnthropicProxy` with `use_proxy=True` routes every call through
a shared infrastructure proxy. Swap the implementation without touching
agent code.

**LLM cloud configuration:** Every agent references an LLM cloud by name.
The admin controls which clouds exist. Agents are isolated from LLM
credentials and routing logic.

**Async token pattern:** Submitting a message returns a token immediately.
The LLM call runs in a FastAPI background task. This pattern maps directly
to a production queue (Celery, ARQ, etc.) with no API changes.

**Agent packages:** An agent is a directory with `agent.yaml`. This is the
unit of version control, deployment, and sharing — the same file that runs
locally can be committed to a repo and deployed by pointing the framework
at the repo clone.

---

## Configuring LLM clouds (`admin_config.yaml`)

```yaml
llm_clouds:
  ollama-llama3:
    provider: ollama
    model: llama3.2
    base_url: "http://localhost:11434"

  anthropic-claude-sonnet:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
    use_proxy: false   # true = route through proxy_endpoint in production

defaults:
  llm_cloud: ollama-llama3
```

---

## Deploying to Render

The `render.yaml` file configures the service. Push to your repo and connect
it to Render — no further configuration needed for the Ollama-free path.

For cloud LLM:
1. Set `ANTHROPIC_API_KEY` in the Render environment variables UI
2. Update `admin_config.yaml` → `defaults.llm_cloud: anthropic-claude-sonnet`
