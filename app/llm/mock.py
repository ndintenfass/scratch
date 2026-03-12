# =============================================================================
# MOCK LLM PROXY — STUB ONLY, FOR UNIT TESTS / PIPELINE TESTING
#
# Returns deterministic minimal responses to verify the API plumbing works.
# It does NOT simulate a realistic conversation.
#
# For realistic demos use:
#   OllamaProxy  — local model, no API key needed (recommended for development)
#   AnthropicProxy — cloud model, requires ANTHROPIC_API_KEY
# =============================================================================
from .base import BaseLLMProxy, LLMRequest, LLMResponse


class MockLLMProxy(BaseLLMProxy):
    """Stub proxy that returns a minimal canned response. For test use only."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Always returns a trivial acknowledgement so tests can verify the pipeline.
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "(no user message)",
        )
        content = (
            f"[MOCK] I received your message: '{last_user_msg[:60]}...'\n"
            f"```json\n{{\"extracted\": {{}}}}\n```"
        )
        return LLMResponse(
            content=content,
            model="mock",
            input_tokens=0,
            output_tokens=0,
        )
