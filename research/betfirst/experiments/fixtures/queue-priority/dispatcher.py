from policy import eligible,dispatch_order

def pick(jobs,now):
    valid=[job for job in jobs if eligible(job,now)]
    return min(valid,key=dispatch_order) if valid else None
