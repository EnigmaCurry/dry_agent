from pydantic import BaseModel, Field
from typing import Literal, Union, List, Annotated


class ContextChangedEvent(BaseModel):
    type: Literal["context_changed"] = Field("context_changed", frozen=True)
    new_context: str


class ContextListEvent(BaseModel):
    type: Literal["context_list"] = Field("context_list", frozen=True)
    contexts: List[str]


Event = Annotated[
    Union[ContextChangedEvent, ContextListEvent], Field(discriminator="type")
]
