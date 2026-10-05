"""llm.py -- YOUR model backend: the one place your code calls Anthropic.

Your stages never touch the SDK. They call

    backend.generate(stage, system, content, schema) -> (parsed, StageCall)

and tests hand them llm_tools.FakeBackend instead. Read the "Calling Claude"
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

    def generate(self, stage, system, content, schema):
        """Send one request and return (validated `schema` instance, StageCall).

        stage    your stage name, e.g. "describe"; use it to pick per-stage settings
        system   the system prompt text
        content  the user message: a list of image and text blocks
        schema   the pydantic class the answer must fit

        It must:
          - send ONE user message with `content`, `system` as the system prompt,
            and `schema` as the structured-output format
          - choose how much the model thinks for each stage (effort)
          - check why the response stopped before trusting it (a refusal or a
            cut-off answer can still be an HTTP 200)
          - retry once if the answer is missing, cut off, declined or invalid;
            then raise LLMError -- never return a half answer
          - return a StageCall with model, total tokens, latency and cost (cost_usd)
        """
        raise NotImplementedError("TODO: implement ClaudeBackend.generate() in llm.py")
