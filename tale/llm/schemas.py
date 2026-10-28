"""Pydantic models for structured LLM output.

Each model defines the expected shape of an LLM response and generates its
own JSON Schema via ``model_json_schema()``. The schema is sent to the backend
via ``response_format`` so generation is constrained to produce valid,
schema-conformant JSON.
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


class ExitSchema(BaseModel):
    direction: str
    name: str
    short_descr: str = ""


class ItemSchema(BaseModel):
    name: str
    type: str = "Other"
    short_descr: str = ""
    level: int = 1
    value: int = 0
    descr: str = ""
    description: str = ""

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if isinstance(obj, str):
            return cls(name=obj)
        if isinstance(obj, dict) and 'description' in obj and 'short_descr' not in obj:
            obj = {**obj, 'short_descr': obj.get('description', '')}
        return super().model_validate(obj, **kwargs)


class NpcSchema(BaseModel):
    name: str
    sentiment: str = ""
    race: str = ""
    gender: str = "n"
    level: int = 1
    aggressive: bool = False
    description: str = ""
    occupation: str = ""
    appearance: str = ""
    type: str = "Npc"
    hp: int = 10
    unarmed_attack: str = "FISTS"


class LocationSchema(BaseModel):
    name: str = ""
    description: str = ""
    exits: List[ExitSchema] = Field(default_factory=list)
    items: List[Union[ItemSchema, str]] = Field(default_factory=list)
    npcs: List[Union[NpcSchema, str]] = Field(default_factory=list)
    indoors: bool = False

    @field_validator('items', mode='before')
    @classmethod
    def _coerce_items(cls, v):
        if isinstance(v, list):
            return [ItemSchema(name=i) if isinstance(i, str) else i for i in v]
        return v

    @field_validator('npcs', mode='before')
    @classmethod
    def _coerce_npcs(cls, v):
        if isinstance(v, list):
            return [NpcSchema(name=n) if isinstance(n, str) else n for n in v]
        return v


class DialogueSchema(BaseModel):
    response: str
    sentiment: str = ""
    give: Optional[str] = None


class ActionSchema(BaseModel):
    goal: str = ""
    thoughts: str = ""
    action: str
    target: str = ""
    text: str = ""
    item: str = ""


class ActionListSchema(BaseModel):
    actions: List[ActionSchema] = Field(default_factory=list)


class FollowSchema(BaseModel):
    response: str
    reason: str = ""


class CharacterSchema(BaseModel):
    name: str
    description: str = ""
    appearance: str = ""
    personality: str = ""
    money: int = 0
    level: int = 1
    gender: str = "n"
    age: int = 30
    race: str = "human"
    occupation: str = ""


class ZoneSchema(BaseModel):
    name: str
    description: str = ""
    races: List[str] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)
    mood: int = 0
    level: int = 1
    size: int = 5


class WorldItemSchema(BaseModel):
    item: ItemSchema


class WorldCreatureSchema(BaseModel):
    creature: NpcSchema


class SpawnSchema(BaseModel):
    items: List[Union[ItemSchema, str]] = Field(default_factory=list)
    npcs: List[NpcSchema] = Field(default_factory=list)
    mobs: List[str] = Field(default_factory=list)

    @field_validator('items', mode='before')
    @classmethod
    def _coerce_spawn_items(cls, v):
        if isinstance(v, list):
            return [ItemSchema(name=i) if isinstance(i, str) else i for i in v]
        return v


class DungeonLocationSchema(BaseModel):
    index: int
    name: str
    description: str = ""


class DungeonLocationsSchema(BaseModel):
    locations: List[DungeonLocationSchema] = Field(default_factory=list)


class DungeonConfigSchema(BaseModel):
    name: str = "Dungeon"
    description: str = ""
    races: List[str] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)
    max_depth: int = 3


class DungeonEntranceSchema(BaseModel):
    direction: str
    name: str
    short_descr: str = ""
    long_descr: str = ""


class NoteQuestSchema(BaseModel):
    reason: str
    type: str = "talk"
    target: str = ""
    location: str = ""
    name: str = ""
