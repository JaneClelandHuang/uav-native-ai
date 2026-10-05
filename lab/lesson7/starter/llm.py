"""llm.py -- YOUR model backend: the one place your code calls Anthropic.

Your stages never touch the SDK. They call

    backend.generate(spec, system, content) -> (parsed, StageCall)

and tests hand them llm_tools.FakeBackend instead. The backend knows nothing
about particular stages: everything stage-specific (name, answer schema,
effort) arrives in the StageSpec you declared in stages.py. Read the "Calling Claude"
part of the HW7 page and the Anthropic docs it links before writing generate().
"""
import _kit  # noqa: F401
from contract import StageCall  # noqa: F401
from llm_tools import LLMError, cost_usd, load_api_key  # noqa: F401

DEFAULT_MODEL = "claude-sonnet-5-5"


class ClaudeBackend:
    def __init__(self, model=None, client=None):
        self.model = model or DEFAULT_MODEL
        if client is None:
            import anthropic
            if not load_api_key():
                raise LLMError("ANTHROPIC_API_KEY is not set (environment or .env)")
            client = anthropic.Anthropic()
        self.client = client

    def generate(self, spec, system, content):
        """Send one request and return (validated spec.schema instance, StageCall).

        spec     the stage's StageSpec: spec.schema (the answer's pydantic class),
                 spec.effort (how hard the model thinks), spec.name (for the StageCall)
        system   the system prompt text
        content  the user message: a list of image and text blocks

        It must:
          - send ONE user message with `content`, `system` as the system prompt,
            and spec.schema as the structured-output format
          - use spec.effort as the effort setting
          - check why the response stopped before trusting it (a refusal or a
            cut-off answer can still be an HTTP 200)
          - retry once if the answer is missing, cut off, declined or invalid;
            then raise LLMError -- never return a half answer
          - return a StageCall (stage=spec.name) with model, total tokens, latency
            and cost (cost_usd)
        """
        raise NotImplementedError("TODO: implement ClaudeBackend.generate() in llm.py")
