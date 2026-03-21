from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

EXTRACTION_INSTRUCTIONS = """
After your conversational response, append a fenced JSON block with any field values you have confidently collected IN THIS TURN OR SO FAR. Use exactly this format:

```json
{"extracted": {"field_name": "value"}}
```

Rules:
- Only include fields where you are confident in the value.
- Omit fields you have not yet gathered.
- Use null for a field only if the user explicitly said they don't have/know it.
- The block must be the very last thing in your response.
"""


def strip_extraction_block(text: str) -> tuple[str, dict[str, Any]]:
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return text.strip(), {}
    try:
        data = json.loads(match.group(1))
        extracted = data.get("extracted", {})
        if not isinstance(extracted, dict):
            extracted = {}
    except json.JSONDecodeError:
        extracted = {}
    clean = text[: match.start()].rstrip() + text[match.end():]
    return clean.strip(), extracted
