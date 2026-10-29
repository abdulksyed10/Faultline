from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ServiceId = Literal["gateway", "checkout", "catalog", "payments", "inventory", "orders", "cache", "database"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Fault(StrictModel):
    service: ServiceId = "database"
    kind: Literal["latency", "saturation", "errors"] = "saturation"
    start: int = Field(default=80, ge=20)
    duration: int = Field(default=100, ge=5)
    severity: float = Field(default=1.2, ge=.2, le=3)


class Scenario(StrictModel):
    name: str = Field(default="Untitled experiment", min_length=1, max_length=100)
    seed: int = Field(default=42, ge=0, le=2**31-1)
    steps: int = Field(default=240, ge=120, le=600)
    traffic: float = Field(default=1, ge=.5, le=2)
    fault: Fault | None = None

    @model_validator(mode="after")
    def valid_window(self):
        if self.fault and self.fault.start + self.fault.duration > self.steps:
            raise ValueError("Fault window must end inside the experiment")
        if not self.name.strip():
            raise ValueError("Experiment name cannot be blank")
        return self


class Repair(StrictModel):
    service: ServiceId
    at: int = Field(ge=0)


class RunRequest(StrictModel):
    scenario: Scenario
    model_id: str | None = Field(default=None, max_length=80)


class TrainRequest(StrictModel):
    epochs: int = Field(default=60, ge=20, le=200)
    seed: int = Field(default=7, ge=0, le=100000)


class BenchmarkRequest(StrictModel):
    model_id: str | None = Field(default=None, max_length=80)
    count: int = Field(default=12, ge=3, le=48)
