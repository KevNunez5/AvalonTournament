
#Roles:
merlin = "Merlin"
good = "Good"
evil = "Evil"

unassigned = "unassigned"
unknown = "unknown"

def is_good(role) -> bool:
    return role == merlin or role == good

def is_evil(role) -> bool:
    return role == evil
    #return not is_good(role) # This doesn't work, because the role could be 'unknown' or 'unassigned'.