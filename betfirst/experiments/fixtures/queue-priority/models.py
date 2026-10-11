from dataclasses import dataclass
@dataclass(frozen=True)
class Job:
    job_id:str
    priority:int
    created:int
    retry_at:int=0
