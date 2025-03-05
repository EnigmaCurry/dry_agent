import instructor
import os
import json
import logging
import time
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import List
from enum import Enum

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# Read config
USE_LLAMA = os.getenv("LLAMA", "true").lower() == "true"
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "stable-code-3b.Q5_K_S.gguf")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
RETRY = int(os.getenv("RETRY", 3))

SYSTEM_PROMPT = (
    "You are an assistant that extracts Docker service actions from user instructions. "
    "Each action must be correctly identified as 'start' or 'stop' based on the user's intent.\n\n"
    "Please return valid JSON with a top-level 'docker_actions' key, e.g:\n"
    "{\n"
    "  \"docker_actions\": [\n"
    "    {\"service_name\": \"immich\", \"action\": \"stop\"},\n"
    "    {\"service_name\": \"postgres\", \"action\": \"stop\"},\n"
    "    {\"service_name\": \"piwigo\", \"action\": \"start\"}\n"
    "  ]\n"
    "}\n"
)
USER_PROMPT = "Stop immich and postgres. Turn on piwigo."

class ActionType(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class DockerAction(BaseModel):
    service: str = Field(..., alias="service_name")
    action: ActionType = Field(...)
    model_config = ConfigDict(populate_by_name=True)

class DockerActionSchema(BaseModel):
    docker_actions: List[DockerAction]

# Utility: Build an OpenAI function schema if you want to do function-calling
def pydantic_model_to_openai_function(model: BaseModel, name: str, description: str) -> dict:
    # Just a quick example – or you can skip function-calling if you prefer
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "docker_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "service_name": {"type": "string"},
                            "action": {
                                "type": "string",
                                "enum": ["start","stop","restart","pause","unpause"]
                            },
                        },
                        "required": ["service_name", "action"]
                    }
                }
            },
            "required": ["docker_actions"]
        },
    }

# Initialize either LLaMA or OpenAI
if USE_LLAMA:
    import llama_cpp
    from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

    llama = llama_cpp.Llama(
        model_path=f"/models/{LLAMA_MODEL}",
        n_gpu_layers=-1,
        chat_format="chatml",
        n_ctx=2048,
        draft_model=LlamaPromptLookupDecoding(num_pred_tokens=2),
        logits_all=True,
        verbose=False,
    )

    create = instructor.patch(
        create=llama.create_chat_completion_openai_v1,
        mode=instructor.Mode.JSON_SCHEMA,
    )

else:
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not provided")

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_ENDPOINT)

    def create_chat_completion(**kwargs):
        return client.chat.completions.create(**kwargs)

    create = instructor.patch(
        create=create_chat_completion,
        mode=instructor.Mode.JSON_SCHEMA,
    )

def get_docker_actions_with_retry(**kwargs) -> DockerActionSchema:
    """
    Tries up to RETRY times, either letting instructor parse (LLaMA)
    or manually parse (OpenAI) if needed.
    """
    for attempt in range(1, RETRY + 1):
        try:
            # 1) LLaMA path – pass response_model
            if USE_LLAMA:
                response = create(response_model=DockerActionSchema, **kwargs)
                return response  # Already a DockerActionSchema

            # 2) OpenAI path – no response_model
            #    We'll parse the function_call ourselves:
            else:
                response = create(**kwargs)
                # function_call approach
                choice = response.choices[0]
                if choice.message.function_call:
                    arguments_str = choice.message.function_call.arguments
                    parsed = json.loads(arguments_str)
                    return DockerActionSchema(**parsed)
                else:
                    # fallback: maybe parse the content as JSON
                    content = choice.message.content
                    data = json.loads(content)
                    return DockerActionSchema(**data)

        except (Exception, ValidationError) as e:
            if attempt < RETRY:
                logging.warning(f"Attempt {attempt}/{RETRY} failed: {e}. Retrying...")
                time.sleep(2 ** (attempt - 1))
            else:
                logging.error("Max retry attempts reached. Reraising exception.")
                raise

# Build params
params = {
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
}

# Optionally add function calling for OpenAI
if not USE_LLAMA:
    # Example function for openai function-calling
    docker_actions_fn = pydantic_model_to_openai_function(
        DockerActionSchema,
        "get_docker_actions",
        "Extract Docker service actions from user instructions"
    )
    params["functions"] = [docker_actions_fn]
    params["function_call"] = {"name": "get_docker_actions"}
    params["model"] = OPENAI_MODEL
else:
    # If using LLaMA, set the llama model in params
    params["model"] = LLAMA_MODEL

# Or if you'd prefer not to do function-calling for OpenAI, skip that
# and rely on the prompt to produce direct JSON.

# If you *didn't* want function calling, you'd remove those lines and
# parse the normal text from `choice.message.content` as JSON.

try:
    docker_actions = get_docker_actions_with_retry(**params)
    print("Parsed Docker Actions:")
    print(docker_actions.model_dump_json(indent=2))
except Exception as e:
    logging.error(f"Failed after {RETRY} attempts: {e}")
