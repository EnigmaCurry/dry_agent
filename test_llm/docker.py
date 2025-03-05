import os
import json
import logging
import time
from enum import Enum
from typing import List

import llama_cpp
from llama_cpp.llama_speculative import LlamaPromptLookupDecoding
import click
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, ConfigDict

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

USE_LLAMA = os.getenv("LLAMA", "true").lower() == "true"
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "Mistral-0.3-7B-Instruct-Q4_K_M.gguf")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
RETRY = int(os.getenv("RETRY", 3))

SYSTEM_PROMPT = (
    "You are an assistant that extracts Docker service actions from user instructions. "
    "Each action must be correctly identified as 'start', 'stop', or 'restart' based on the user's intent. 'turn on' means the same thing as 'start' and 'turn off' means the same thing as 'stop'."
)

class ActionType(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"

class DockerAction(BaseModel):
    service: str = Field(..., alias="service_name")
    action: ActionType = Field(...)
    model_config = ConfigDict(populate_by_name=True)

class DockerActionSchema(BaseModel):
    docker_actions: List[DockerAction]

def pydantic_schema_to_openai_parameters(pydantic_schema: dict) -> dict:
    """Recursively expand any $ref references from Pydantic JSON schema into a single dict."""
    definitions = pydantic_schema.pop("definitions", {})

    def expand_refs(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].split("/")[-1]
                sub_schema = definitions.get(ref_name, {})
                return expand_refs(sub_schema)
            else:
                return {k: expand_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_refs(item) for item in obj]
        else:
            return obj

    return expand_refs(pydantic_schema)

def pydantic_model_to_openai_function(model: BaseModel, name: str, description: str) -> dict:
    """Build an OpenAI function schema from a Pydantic model."""
    raw_schema = model.model_json_schema()
    raw_schema.pop("title", None)
    parameters_schema = pydantic_schema_to_openai_parameters(raw_schema)
    return {
        "name": name,
        "description": description,
        "parameters": parameters_schema,
    }

if USE_LLAMA:
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
            if USE_LLAMA:
                response = create(response_model=DockerActionSchema, **kwargs)
                return response  # Already a DockerActionSchema

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

@click.command()
@click.argument("user_prompt")
def main(user_prompt: str):
    """
    Simple CLI to parse user instructions about Docker services.
    The user_prompt is a required positional argument.
    """
    params = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    }

    if not USE_LLAMA:
        docker_actions_fn = pydantic_model_to_openai_function(
            DockerActionSchema,
            "get_docker_actions",
            "Extract Docker service actions from user instructions"
        )
        params["functions"] = [docker_actions_fn]
        params["function_call"] = {"name": "get_docker_actions"}
        params["model"] = OPENAI_MODEL
    else:
        params["model"] = LLAMA_MODEL

    try:
        docker_actions = get_docker_actions_with_retry(**params)
        print("Parsed Docker Actions:")
        print(docker_actions.model_dump_json(indent=2))
    except Exception as e:
        logging.error(f"Failed after {RETRY} attempts: {e}")

if __name__ == "__main__":
    main()
