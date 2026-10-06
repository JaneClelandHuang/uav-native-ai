"""llm.py -- the model backend: the one place the pipeline calls Anthropic.

GIVEN COMPLETE. This is the ClaudeBackend walked through line by line in
class. Read it until you can explain every line (questions Q6-Q9 ask about
it); you may change it (e.g. DEFAULT_MODEL), but you don't have to.

Your stages never touch the SDK. They call

    backend.generate(spec, system, content) -> (parsed, StageCall)

and tests hand them llm_tools.FakeBackend instead. The backend knows nothing
about particular stages: the answer schema and effort arrive in the
StageSpec each stage declares in stages.py.

What generate() does, in order:
  1. sends ONE user message (`content`: image and text blocks) with `system`
     as the system prompt, spec.schema as the structured-output format and
     spec.effort as the effort
  2. checks why the response stopped before trusting it: a refusal or a
     cut-off answer can still be an HTTP 200
  3. retries once if the answer is missing, cut off, declined or invalid,
     then raises LLMError -- it never returns a half answer
  4. returns the validated answer and a StageCall (tokens, latency, cost)
"""
import time

import _kit  # noqa: F401
from contract import StageCall  # noqa: F401
from llm_tools import KEY_HELP, LLMError, cost_usd, load_api_key  # noqa: F401

DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 8000
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeBackend:
    def __init__(self, model=None, client=None):
        self.model = model or DEFAULT_MODEL
        if client is None:
            import anthropic
            if not load_api_key():
                raise LLMError(KEY_HELP)
            client = anthropic.Anthropic()
        self.client = client

    def generate(self, spec, system, content):
        import anthropic
        import pydantic
        model = self.model
        started = time.monotonic()
        in_tok = out_tok = 0
        problem = None
        for attempt in (1, 2):
            try:
                response = self.client.beta.messages.parse(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    messages=[{"role": "user", "content": content}],
                    output_format=spec.schema,
                    output_config={"effort": spec.effort},
                    betas=[FALLBACK_BETA],
                    fallbacks="default",
                )
            except (pydantic.ValidationError, ValueError) as exc:
                # The SDK raised while parsing, so this attempt's usage isn't available:
                # its tokens are missing from the StageCall (cost slightly under-reported).
                problem = f"invalid output: {exc}"
                continue
            except anthropic.APIStatusError as exc:
                raise LLMError(f"{spec.name}: API error {exc.status_code}: {exc.message}") from exc
            in_tok += response.usage.input_tokens
            out_tok += response.usage.output_tokens
            if response.stop_reason == "refusal":
                problem = "model declined the request"
            elif response.stop_reason == "max_tokens":
                problem = "response cut off at max_tokens"
            elif response.parsed_output is None:
                problem = "no parsable output"
            else:
                call = StageCall(stage=spec.name, model=model, input_tokens=in_tok, output_tokens=out_tok,
                                 latency_s=round(time.monotonic() - started, 2),
                                 cost_usd=round(cost_usd(model, in_tok, out_tok), 5), attempts=attempt)
                return response.parsed_output, call
        raise LLMError(f"{spec.name}: {problem} (after 2 attempts)")
