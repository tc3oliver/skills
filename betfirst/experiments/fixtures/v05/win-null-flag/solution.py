def effective_flag(options, default=True):
    return options.get('enabled') or default
