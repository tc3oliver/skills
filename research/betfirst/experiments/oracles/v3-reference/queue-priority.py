from pathlib import Path
p=Path("policy.py")
s=p.read_text()
assert "(job.created,-job.priority,job.job_id)" in s
p.write_text(s.replace("(job.created,-job.priority,job.job_id)","(-job.priority,job.created,job.job_id)"))
