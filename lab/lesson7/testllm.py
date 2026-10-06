#!/usr/bin/env python3
"""testllm.py -- check that your Anthropic API key works. Costs a fraction of a cent.

    cd lab/lesson7
    python testllm.py

It finds your key the same way the HW7 tools do (the .env in the top folder
of your repo), asks Claude one tiny question, and prints the answer, where
the key came from, and what the call cost.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from llm_tools import KEY_HELP, REPO_ROOT_ENV, cost_usd, load_api_key  # noqa: E402

MODEL = "claude-sonnet-5-5"   # the HW7 default model


def main():
    in_shell = bool(os.environ.get("ANTHROPIC_API_KEY"))
    key = load_api_key()
    if not key:
        sys.exit(KEY_HELP)
    if in_shell:
        print("Key found in your SHELL ENVIRONMENT (an exported ANTHROPIC_API_KEY).")
        print("  Warning: Claude Code can pick that up and bill your everyday use to this key.")
        print(f"  Better: remove the export and keep the key only in {REPO_ROOT_ENV}\n")
    else:
        print(f"Key found in {REPO_ROOT_ENV if os.path.isfile(REPO_ROOT_ENV) else 'a .env file'}  "
              f"(ends ...{key[-4:]})")

    import anthropic
    client = anthropic.Anthropic(api_key=key)
    try:
        raw = client.messages.with_raw_response.create(
            model=MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": "In one short sentence: what is a drone?"}],
        )
    except anthropic.AuthenticationError:
        sys.exit("FAILED: the key was rejected (401). Check that you copied all of it into .env.")
    except anthropic.PermissionDeniedError as exc:
        sys.exit(f"FAILED: permission denied (403): {exc.message}")
    except anthropic.RateLimitError as exc:
        sys.exit(f"FAILED: rate or spend limit reached (429): {exc.message}")
    except anthropic.APIStatusError as exc:
        sys.exit(f"FAILED: API error {exc.status_code}: {exc.message}")
    except anthropic.APIConnectionError:
        sys.exit("FAILED: couldn't reach api.anthropic.com. Check your internet connection.")

    message = raw.parse()
    if message.stop_reason == "refusal":
        sys.exit("FAILED: the model declined this request. Tell your instructor.")
    answer = "".join(block.text for block in message.content if block.type == "text").strip()
    cost = cost_usd(MODEL, message.usage.input_tokens, message.usage.output_tokens)
    print(f"\nClaude says: {answer}\n")
    print(f"OK: your key works.  model {MODEL}, workspace {raw.headers.get('anthropic-workspace-id')}, "
          f"cost ${cost:.5f}")


if __name__ == "__main__":
    main()
