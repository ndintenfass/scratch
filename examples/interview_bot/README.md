# Customer Discovery Bot — Agent Package

This directory is an **agent package**: a self-contained, version-controlled
definition of a live interview agent.

## What it does

Conducts structured discovery interviews with prospects to capture:

- Their role and company context
- Primary pain points and current solutions
- Decision-making process
- Budget hints and buying timeline

The bot conducts the interview naturally and conversationally — it does not
ask questions like a form; it guides the conversation to surface information
organically, using keyword triggers and segmentation rules to adapt its approach.

## Package contents

```
interview_bot/
├── agent.yaml   ← the declarative spec (required in every package)
└── README.md    ← this file (optional)
```

## Deploying this agent

### Via package path (from the repo)

```bash
curl -X POST http://localhost:8000/agents/from-package \
  -H "Content-Type: application/json" \
  -d '{"package_path": "./examples/interview_bot"}'
```

### Via inline spec

```bash
# Parse agent.yaml to JSON first, then:
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"spec": <agent.yaml contents as JSON>}'
```

Both return: `{"agent_id": "agent_abc123", "status": "active", ...}`

## Running a conversation

```bash
AGENT_ID="agent_abc123"

# Start a conversation
curl -X POST http://localhost:8000/agents/$AGENT_ID/conversations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi! I run a 20-person SaaS startup and we'\''re struggling with customer onboarding."}'

# Returns: {"token": "tok_xyz", "conversation_id": "conv_abc", ...}

TOKEN="tok_xyz"
CONV_ID="conv_abc"

# Poll for result
curl http://localhost:8000/agents/$AGENT_ID/conversations/$TOKEN

# Continue the conversation
curl -X POST http://localhost:8000/agents/$AGENT_ID/conversations \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"We use a mix of Notion and email, it'\''s a mess.\", \"conversation_id\": \"$CONV_ID\"}"
```

## Customising this agent

Edit `agent.yaml` to:
- Change the `topic` and `tone`
- Add or remove fields from `metadata_to_collect`
- Adjust `keyword_triggers` for your domain
- Change `llm_cloud` to use a different model (see `admin_config.yaml`)
- Switch `extraction.strategy` if the default JSON block extraction is unreliable with your model
