from pydantic import BaseModel
from typing import Any, List, Optional

class AnalyzeRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = None # Auto-detect if None

class AnalysisResponse(BaseModel):
    message: str
    repo_id: str

class QueryRequest(BaseModel):
    repo_id: str
    query: str

class PushRequest(BaseModel):
    repo_url: str
    file_path: str
    content: str
    commit_message: str
    branch: Optional[str] = "main"

class AuditRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    file_path: str
    diff_content: str

class AuditResponse(BaseModel):
    outcome: str
    audit_summary: str
    findings: List[dict]
    healed_content: Optional[str] = None
    simulation: dict
    transcript: List[dict]
