import llama_cpp
import instructor
from llama_cpp.llama_speculative import LlamaPromptLookupDecoding
from pydantic import BaseModel
from typing import List

llama = llama_cpp.Llama(
    model_path="/models/tinyllama-1.1b-chat-v1.0.Q8_0.gguf",
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


class Character(BaseModel):
    name: str
    occupation: str
    personality: str
    background: str


class CharactersSchema(BaseModel):
    characters: List[Character]

characters = create(
    messages=[
        {
            "role": "user",
            "content": "Make up three new non-canonical Star Trek characters. Make sure each one has a realistic name, occupation, personality, and background.",
        }
    ],
    response_model=CharactersSchema,
    temperature=0.7,
    top_p=0.9
)

print(characters.model_dump_json(indent=4))
