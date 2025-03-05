import instructor
import os
import json
import logging
import time
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import List
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# Configurable options
USE_LLAMA = os.getenv("LLAMA", "true").lower() == "true"
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "stable-code-3b.Q5_K_S.gguf")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")

# Retry attempts
RETRY = int(os.getenv("RETRY", 3))

SYSTEM_PROMPT = (
    "You are an assistant that extracts Docker service actions from user instructions. "
    "Each action must be correctly identified as 'start' or 'stop' based on the user's intent."
)
USER_PROMPT = "Stop immich and postgres. Turn on piwigo."

class ActionType(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class DockerAction(BaseModel):
    # We use "service_name" in the JSON so it aligns with LLM outputs
    service: str = Field(..., alias="service_name", description="Name of the Docker service.")
    action: ActionType = Field(..., description="Docker action to be performed on the service.")
    model_config = ConfigDict(populate_by_name=True)

class DockerActionSchema(BaseModel):
    docker_actions: List[DockerAction] = Field(
        ...,
        description="List of Docker actions to execute."
    )

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


###############################################################################
# Initialize either LLaMA or OpenAI
###############################################################################
if USE_LLAMA:
    import llama_cpp
    from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

    logging.debug("Initializing LLaMA model...")
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

    logging.debug("Initializing OpenAI API client...")
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_ENDPOINT)

    def create_chat_completion(**kwargs):
        return client.chat.completions.create(**kwargs)

    create = instructor.patch(
        create=create_chat_completion,
        mode=instructor.Mode.JSON_SCHEMA,
    )

###############################################################################
# Retry the entire flow (request + parse) up to RETRY times with backoff
###############################################################################
def get_docker_actions_with_retry(**kwargs) -> DockerActionSchema:
    """Attempts the ChatCompletion call up to RETRY times, each time parsing JSON into DockerActionSchema."""
    for attempt in range(1, RETRY + 1):
        try:
            response = create(**kwargs)

            if USE_LLAMA:
                # LLaMA + instructor mode. Usually "response" might be
                # a Pydantic model or a dict that includes top-level keys like
                # "id", "object", "choices" etc.
                #
                # We want to get the actual JSON that contains "docker_actions".
                # If instructor is returning the actual schema, you might do:
                #   data = response.dict()
                # but in "mode=instructor.Mode.JSON_SCHEMA" it might be
                # returning a pydantic parse directly.
                #
                # 1) Check if 'docker_actions' is already in response.model_dump():
                data = response.model_dump()
                debug_data = response.model_dump_json(indent=4)
                print("DEBUG LLaMA JSON:\n", debug_data)

                if "docker_actions" in data:
                    # If your LLaMA response is a direct match to DockerActionSchema:
                    return DockerActionSchema(**data)
                else:
                    # Possibly the JSON is nested in something like data["json"] or data["content"]
                    # or data["choices"][0]["message"], depending on how your model is responding.
                    #
                    # For example, if the JSON is in data["json"]:
                    #   content = data.get("json", {})
                    #   return DockerActionSchema(**content)
                    #
                    # For now, let's assume the model might have put the schema in data["choices"][0]["message"]...
                    # You may need to adjust based on actual debugging prints:
                    choices = data.get("choices", [])
                    if choices and isinstance(choices, list):
                        # Each choice might contain a parsed dictionary with "docker_actions"
                        first_choice = choices[0]
                        # If the schema is nested:
                        if "docker_actions" in first_choice:
                            return DockerActionSchema(**first_choice)

                    raise ValueError("No 'docker_actions' found in LLaMA response.")
            else:
                # OpenAI function calling
                choice = response.choices[0]
                function_call = choice.message.function_call
                if function_call:
                    arguments_str = function_call.arguments
                    parsed_data = json.loads(arguments_str)
                    return DockerActionSchema(**parsed_data)
                else:
                    raise ValueError("No function call in OpenAI response.")

        except (Exception, ValidationError) as e:
            if attempt < RETRY:
                logging.warning(f"Attempt {attempt}/{RETRY} failed with error: {e}. Retrying...")
                time.sleep(2 ** (attempt - 1))  # exponential backoff
            else:
                logging.error("Max retry attempts reached. Raising exception.")
                raise

###############################################################################
# Build the request parameters
###############################################################################
params = {
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
}

if USE_LLAMA:
    params["model"] = LLAMA_MODEL
else:
    docker_actions_function = pydantic_model_to_openai_function(
        model=DockerActionSchema,
        name="get_docker_actions",
        description="Extract Docker service actions from user instructions"
    )
    params["model"] = OPENAI_MODEL
    params["functions"] = [docker_actions_function]
    params["function_call"] = {"name": "get_docker_actions"}

###############################################################################
# Final usage
###############################################################################
try:
    docker_actions = get_docker_actions_with_retry(**params)
    print(docker_actions.model_dump_json(indent=2))
except Exception as e:
    logging.error(f"Failed to get Docker actions after {RETRY} attempts: {e}")
