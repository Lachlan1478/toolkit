from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

class MVPCriteria(BaseModel):
    target_user: str
    primary_outcome: str
    must_haves: List[str]
    ux_rules: List[str] = []
    non_goals: List[str] = []
    perf: Dict[str, Any] = {}
    accessibility: Dict[str, Any] = {}
    max_iterations: int = 3

class AppSpec(BaseModel):
    name: str
    screens: List[Dict[str, Any]]
    interaction: Dict[str, Any]
    theme: Literal["minimal-dark", "light"] = "minimal-dark"
    datasources: Dict[str, str]
    acceptance_tests: List[Dict[str, Any]]

class ChangeRequest(BaseModel):
    app_id: str
    reason: str
    changes: List[Dict[str, Any]]
