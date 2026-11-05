from pydantic import BaseModel
from typing import List, Dict, Optional

class ARCExample(BaseModel):
    input: List[List[int]]
    output: List[List[int]]

class ARCTask(BaseModel):
    task_id: Optional[str] = None
    train: List[ARCExample]
    test: List[ARCExample]

class SolveRequest(BaseModel):
    task: ARCTask
    use_cache: bool = True
    strategy: Optional[str] = None  # auto, identity, color_map, symmetry_h, symmetry_v, constant, background

class SolveResponse(BaseModel):
    success: bool
    task_id: Optional[str]
    source: str  # cache, identity, color_map, symmetry_h, symmetry_v, constant, background, failed
    prediction: Optional[List[List[int]]]
    scores: Optional[Dict[str, float]]
    error: Optional[str] = None

class TaskFilter(BaseModel):
    category: Optional[str] = None
    solver: Optional[str] = None
    version: Optional[str] = None
