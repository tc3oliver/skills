def eligible(job,now):return job.retry_at<=now

def dispatch_order(job):return (job.created,-job.priority,job.job_id)
