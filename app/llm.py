import os

from dotenv import load_dotenv
from anthropic import Anthropic

from app.schemas import Classification

load_dotenv()

_MODEL = "claude-sonnet-5"
_TOOL_NAME = "record_classification"

_SYSTEM_PROMPT = (
    "You are a clinical assistant that detects cognitive distortions in a piece "
    "of text. Analyze the text and call the record_classification tool with your "
    "classification. If no distortion is present, use distortion 'none'."
)

_TOOLS = [
    {
        "name": _TOOL_NAME,
        "description": "Record the cognitive distortion classification for the given text.",
        "input_schema": Classification.model_json_schema(),
    }
]

_client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={
        "anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID"]
    }
)

def classify(text: str) -> tuple[Classification, dict]:
    response = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=_TOOLS,
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": text}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == _TOOL_NAME:
            result = Classification.model_validate(block.input) # Pydantic validates here
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": response.model,
            }
            return result, usage

    raise ValueError("Model response did not include a record_classification tool call")
