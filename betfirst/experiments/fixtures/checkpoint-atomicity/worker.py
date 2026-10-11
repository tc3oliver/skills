def process(items,checkpoint,sink):
    for index in range(checkpoint.cursor,len(items)):
        checkpoint.advance(index+1)
        sink(items[index])
    return checkpoint.cursor
