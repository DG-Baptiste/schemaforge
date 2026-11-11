"""Domain models for the selected vacancy extraction scenario."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class Vacancy(BaseModel):
    """Validated job-vacancy record used in the demo and evaluation data."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    employment_type: EmploymentType | None = None
    published_at: date | None = None
    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def salary_range_is_valid(self) -> Vacancy:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")
        return self
