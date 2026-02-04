from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from database.models import MovieStatusEnum


class CountrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: Optional[str] = None


class GenreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ActorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class LanguageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MovieListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int


class MovieDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]


class MovieCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: str
    genres: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        if len(v) > 255:
            raise ValueError("Name must not exceed 255 characters")
        return v

    @field_validator("date")
    @classmethod
    def validate_date_not_too_far_future(cls, v: date) -> date:
        if v > (date.today() + timedelta(days=365)):
            raise ValueError("Date must not be more than one year in the future")
        return v

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator("budget", "revenue")
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("country")
    @classmethod
    def normalize_country_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not (2 <= len(v) <= 3):
            raise ValueError("Country code must be 2-3 characters")
        return v

    @field_validator("genres", "actors", "languages")
    @classmethod
    def normalize_string_lists(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in v:
            s = str(item).strip()
            if s:
                cleaned.append(s)
        return cleaned


class MovieUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = None
    revenue: Optional[float] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        if len(v) > 255:
            raise ValueError("Name must not exceed 255 characters")
        return v

    @field_validator("date")
    @classmethod
    def validate_date_not_too_far_future(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        if v > (date.today() + timedelta(days=365)):
            raise ValueError("Date must not be more than one year in the future")
        return v

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (0 <= v <= 100):
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator("budget", "revenue")
    @classmethod
    def validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class MessageSchema(BaseModel):
    detail: str
