from pydantic import BaseModel, Field
from typing import Literal, Union, List, Annotated


class LogoutEvent(BaseModel):
    type: Literal["logout"] = Field("logout", frozen=True)


class ContextChangedEvent(BaseModel):
    type: Literal["context_changed"] = Field("context_changed", frozen=True)
    new_context: str


class ContextListEvent(BaseModel):
    type: Literal["context_list"] = Field("context_list", frozen=True)
    contexts: List[str]


class OpenAppEvent(BaseModel):
    type: Literal["open_app"] = Field("open_app", frozen=True)
    page: str


class OpenInstancesEvent(BaseModel):
    type: Literal["open_instances"] = Field("open_instances", frozen=True)
    app: str


class OpenURLEvent(BaseModel):
    type: Literal["open_url"] = Field("open_url", frozen=True)
    url: str


Event = Annotated[
    Union[ContextChangedEvent, ContextListEvent], Field(discriminator="type")
]
