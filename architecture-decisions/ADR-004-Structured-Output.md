# ADR-004 — Structured Output via Tool-Calling


## Problem
Everything downstream — storage, routing, evaluation — must trust the *shape* of the classifier's output. A free-text LLM response can't be relied on: it varies, and parsing failures surface in production, not in testing.

## Options considered
- **Prompt-and-parse** — ask the model to "reply in JSON", then `json.loads`/regex. Works most of the time; fails silently and unpredictably.
- **Tool-calling / structured-output mode** — pass a Pydantic JSON schema as a tool and force the model to fill it; validate the result with Pydantic.
- **Fine-tune for format** — reliable but heavy overkill for this.

## Decision
Define the output as a **Pydantic model**, pass its JSON schema to the provider as a **forced tool call**, and **validate** the returned object with Pydantic.

## Why
- Constrains the least reliable component in the system to a fixed contract.
- Invalid values (a confidence of 1.7, a distortion outside the enum) fail at object construction and are handled explicitly, rather than propagating downstream.
- The same schema documents the API response and mirrors the database shape — one definition, several uses.
- Works consistently across both Claude and OpenAI.

## Trade-offs
- Slightly more tokens/latency than a bare prompt.
- Couples to provider tool-calling APIs — abstracted behind a small interface so a provider swap is contained.
- Deliberately rigid: unsuitable for open-ended generation (fine here — the *reframing* stage is a separate, freer step).

## When I'd choose something else
- **Prompt-and-parse** for a quick throwaway prototype where reliability doesn't matter.
- **Free-form output** for the creative/long-form parts of the system where a fixed structure would get in the way.
