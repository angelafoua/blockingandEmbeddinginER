def is_match(r1, r2):

    if r1.get("ssn") and r1["ssn"] == r2.get("ssn"):
        return True

    score = 0

    if r1.get("phone") == r2.get("phone"):
        score += 2

    if r1.get("last_name") == r2.get("last_name"):
        score += 1

    if r1.get("address") == r2.get("address"):
        score += 1

    return score >= 2
