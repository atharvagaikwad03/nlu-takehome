import re


def normalizeAddress(s: str) -> str:
    # ingest and API both use this if they diverge, address lookups miss rows
    if not s:
        return ""
    s = s.strip() # removes any whitespace
    s = s.lower() # converts to lowercase
    # collapse multiple spaces/tabs to one
    s = re.sub(r"\s+", " ", s) # converts to multiple spaces to one space
    return s
