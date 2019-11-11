"""
other tools that might be used 
that are not necessarily actions
"""

def has_keywords(s, words):
    """searches a string for a list of words. 
    if one is found, return true"""
    for word in words:
        if word in s:
            return True
    return False