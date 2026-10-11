def retry_once(call, transient=(TimeoutError,)):
    try:return call()
    except transient:return call()
