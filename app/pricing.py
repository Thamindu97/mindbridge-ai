PRICING = {
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "gpt-5.6": {"input": 1.75, "output": 14.00},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    pricing = PRICING.get(model)
    if pricing is None:
        return None

    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
