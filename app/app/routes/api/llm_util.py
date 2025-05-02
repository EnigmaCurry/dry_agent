from openai import AsyncOpenAI

client = AsyncOpenAI()


async def generate_title(
    message: str,
    model: str = "gpt-3.5-turbo",
    max_tokens: int = 10,
    temperature: float = 0.5,
) -> str:
    """
    Generate a concise title summarizing the input message.

    Uses the AsyncOpenAI client (no need to set api_key in code
    if you've exported OPENAI_API_KEY or set up your config file).

    Args:
        message:      Text to summarize.
        model:        Model name.
        max_tokens:   Max tokens for the title.
        temperature:  Sampling temperature.

    Returns:
        One-line title.
    """
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that writes very short titles.",
            },
            {
                "role": "user",
                "content": (
                    "Create a brief title (≤5 words) summarizing the following:\n\n"
                    f"{message}"
                ),
            },
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    # strip quotes/newlines
    return resp.choices[0].message.content.strip().strip('"“”')
