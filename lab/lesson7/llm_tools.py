"""llm_tools.py -- given helpers for the model layer. Do not edit.

Your ClaudeBackend (in your own llm.py) makes the real Anthropic call. These
are the pieces around it:

    image_block(b64, media_type)   an Anthropic image content block (base64 PNG/JPEG)
    load_api_key()                 ANTHROPIC_API_KEY from the environment or a .env file
    PRICES, cost_usd(...)          list prices per million tokens -> dollars for a StageCall
    LLMError                       raise this when a stage can't get a valid answer
    FakeBackend                    scripted answers, for unit tests without the API
    TracingBackend                 wraps any backend and prints every call (evaluate.py uses it)

Every backend has the same method:

    backend.generate(spec, system, content) -> (validated spec.schema instance, StageCall)

spec    a contract.StageSpec you declared in stages.py: its name, its answer
        schema and its effort travel together, so no backend keeps a table of
        stage names
system  the system prompt text (your prompts/<spec.name>.md)
content the user message content: a list of image and text blocks
"""
import base64
import os

from contract import StageCall, StageSpec

# $ per million tokens (input, output) -- Anthropic list prices, Sept 2026.
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-opus-5-5": (4.00, 20.00),
}


class LLMError(RuntimeError):
    """The model could not produce a valid answer for a stage."""


def image_block(png_or_jpeg_b64, media_type="image/png"):
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": png_or_jpeg_b64}}


def image_block_from_file(path):
    media_type = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
    with open(path, "rb") as f:
        return image_block(base64.standard_b64encode(f.read()).decode("ascii"), media_type)


REPO_ROOT_ENV = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))
KEY_HELP = (f"ANTHROPIC_API_KEY is not set. Put this line in {REPO_ROOT_ENV} (it is gitignored):\n"
            f"    ANTHROPIC_API_KEY=sk-ant-...")


def load_api_key():
    """ANTHROPIC_API_KEY from the environment, else from a .env file.

    Checked in order, stopping at the first that has the key: the repo-root
    .env (where HW7 says to put it), the nearest .env above the current
    folder, then ~/.env. The repo root is checked explicitly because lab/.env
    (the drone configuration from SETUP.md) is nearer to lab/lesson7 and
    would otherwise be the only one found.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    try:
        from dotenv import dotenv_values, find_dotenv
    except ImportError:
        return None
    for path in (REPO_ROOT_ENV, find_dotenv(usecwd=True), os.path.expanduser("~/.env")):
        if path and os.path.isfile(path):
            key = dotenv_values(path).get("ANTHROPIC_API_KEY")
            if key:
                os.environ["ANTHROPIC_API_KEY"] = key
                return key
    return None


def cost_usd(model, input_tokens, output_tokens):
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class FakeBackend:
    """Scripted answers for tests: {spec: [answer, answer, ...]} where each key
    is one of your StageSpecs (or its name) and each answer is a pydantic
    object, a dict (validated against spec.schema), or an Exception to raise.
    Records every request in .requests."""

    def __init__(self, script):
        self.script = {(k.name if isinstance(k, StageSpec) else k): list(v) for k, v in script.items()}
        self.requests = []

    def generate(self, spec, system, content):
        self.requests.append({"stage": spec.name, "spec": spec, "system": system, "content": content})
        answers = self.script.get(spec.name)
        if not answers:
            raise AssertionError(f"FakeBackend has no scripted answer left for stage {spec.name!r}")
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, dict):
            answer = spec.schema.model_validate(answer)
        return answer, StageCall(stage=spec.name, model="fake", input_tokens=0, output_tokens=0,
                                 latency_s=0.0, cost_usd=0.0)


class TracingBackend:
    """Wraps another backend and shows every stage call as it happens:
    the system prompt (file + first line, or all of it), the text sent, each
    image sent (size, and saved to image_dir so you can open it), then the
    model's validated answer, tokens, cost and latency.

        backend = TracingBackend(ClaudeBackend(), image_dir="data/trace/lp01")
    """

    def __init__(self, inner, image_dir=None, show_system=False, write=print):
        self.inner = inner
        self.image_dir = image_dir
        self.show_system = show_system
        self.write = write
        self.n = 0

    def generate(self, spec, system, content):
        self.n += 1
        w = self.write
        stage = spec.name
        w(f"\n  ┌─ call {self.n}: {stage.upper()}  (expects {spec.schema.__name__}, effort {spec.effort})")
        if self.show_system:
            w("  │ SYSTEM PROMPT:")
            for line in system.strip().splitlines():
                w(f"  │   {line}")
        else:
            first = system.strip().splitlines()[0]
            w(f"  │ system: prompts/{stage}.md -- \"{first[:90]}{'...' if len(first) > 90 else ''}\"")
        images = 0
        for block in content:
            if block["type"] == "image":
                images += 1
                w(f"  │ IMAGE {images}: {self._image_info(stage, images, block)}")
            elif block["type"] == "text":
                w("  │ TEXT:")
                for line in block["text"].splitlines():
                    w(f"  │   {line}")
        try:
            result, call = self.inner.generate(spec, system, content)
        except Exception as exc:
            w(f"  └─ FAILED: {exc}")
            raise
        w(f"  │ ── model answer ({call.model}, {call.input_tokens} in / {call.output_tokens} out tokens, "
          f"${call.cost_usd:.4f}, {call.latency_s:.1f} s{', attempt ' + str(call.attempts) if call.attempts > 1 else ''}):")
        for line in result.model_dump_json(indent=2).splitlines():
            w(f"  │   {line}")
        w("  └─")
        return result, call

    def _image_info(self, stage, k, block):
        import io
        data = base64.b64decode(block["source"]["data"])
        info = f"{len(data) // 1024} KB {block['source']['media_type']}"
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as im:
                info = f"{im.width}x{im.height} px, " + info
        except Exception:
            pass
        if self.image_dir:
            os.makedirs(self.image_dir, exist_ok=True)
            ext = "jpg" if "jpeg" in block["source"]["media_type"] else "png"
            path = os.path.join(self.image_dir, f"{self.n:02d}-{stage}-img{k}.{ext}")
            with open(path, "wb") as f:
                f.write(data)
            info += f" -> {path}"
        return info
