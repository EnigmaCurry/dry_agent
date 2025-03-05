import instructor
import os
import json
import logging
from pydantic import BaseModel
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

# Prompts
SYSTEM_PROMPT = (
    "You are an assistant that extracts Docker service actions from user instructions. "
    "Each action must be correctly identified as 'start' or 'stop' based on the user's intent."
)
USER_PROMPT = "Stop immich and postgres. Turn on piwigo."


logging.debug(f"Using Llama: {USE_LLAMA}")
if not USE_LLAMA:
    logging.debug(f"OpenAI API Key: {'Set' if OPENAI_API_KEY else 'Not Set'}")
    logging.debug(f"OpenAI Model: {OPENAI_MODEL}")
    logging.debug(f"OpenAI Endpoint: {OPENAI_ENDPOINT}")

class ActionType(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class DockerAction(BaseModel):
    service: str
    action: ActionType

class DockerActionSchema(BaseModel):
    docker_actions: List[DockerAction]

if USE_LLAMA:
    # -- LLaMA path (unchanged) --
    import llama_cpp
    from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

    logging.debug("Initializing Llama model...")
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
    # -- OpenAI path with function calling --
    from openai import OpenAI

    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not provided")
        raise RuntimeError("OPENAI_API_KEY is not provided")

    logging.debug("Initializing OpenAI API client...")
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_ENDPOINT)

    # Define the JSON schema to parse Docker actions
    docker_actions_function = {
        "name": "get_docker_actions",
        "description": "Extract Docker service actions from user instructions",
        "parameters": {
            "type": "object",
            "properties": {
                "docker_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "service": {"type": "string"},
                            "action": {
                                "type": "string",
                                "enum": ["start", "stop", "restart", "pause", "unpause"],
                            },
                        },
                        "required": ["service", "action"]
                    }
                }
            },
            "required": ["docker_actions"]
        }
    }

    def create_chat_completion(**kwargs):
        logging.debug(f"Calling OpenAI API with parameters:\n{json.dumps(kwargs, indent=4)}")
        try:
            response = client.chat.completions.create(**kwargs)
            logging.debug(f"OpenAI API Response:\n{response}")
            return response
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            raise

    create = instructor.patch(
        create=create_chat_completion,
        mode=instructor.Mode.JSON_SCHEMA,
    )

# Prepare parameters for the request
params = {
    "model": OPENAI_MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ],
}

# If using OpenAI, add function-calling arguments
if not USE_LLAMA:
    params["functions"] = [docker_actions_function]
    # Force the model to call the function `get_docker_actions`:
    params["function_call"] = {"name": "get_docker_actions"}

logging.debug("Sending request to LLM...")
try:
    # Send request
    response = create(**params)

    # Print the raw response (or raw JSON from the LLaMA path)
    logging.debug("Received response from LLM.")

    if USE_LLAMA:
        # LLaMA path result is already JSON-schematized by `instructor`
        print(json.dumps(response.model_dump(), indent=4))
    else:
        # OpenAI function calling
        # The model output is in response.choices[0].message["function_call"] if a function call was made
        choice = response.choices[0]
        function_call = choice.message.function_call
        if function_call:
            name = function_call.name
            arguments_str = function_call.arguments

            logging.debug(f"Function called: {name}")
            logging.debug(f"Arguments (JSON string): {arguments_str}")

            # Parse JSON arguments with pydantic
            arguments_dict = json.loads(arguments_str)
            docker_actions = DockerActionSchema(**arguments_dict)
            print("Parsed Docker Actions:", docker_actions.model_dump_json(indent=4))
        else:
            # If the model didn't call the function, just print the text content
            print("Assistant response:", choice.message["content"])

except Exception as e:
    logging.error(f"Failed to get response: {e}")
