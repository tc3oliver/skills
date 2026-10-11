def merge_sorted(left,right,key=lambda x:x):
    out=[];i=j=0
    while i<len(left) and j<len(right):
        if key(left[i])<=key(right[j]):out.append(left[i]);i+=1
        else:out.append(right[j]);j+=1
    return out+list(left[i:])+list(right[j:])
