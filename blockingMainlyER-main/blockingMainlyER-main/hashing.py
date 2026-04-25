from collections import Counter

def soundex(name):
    name = name.upper()
    mapping = {"BFPV":"1","CGJKQSXZ":"2","DT":"3","L":"4","MN":"5","R":"6"}

    result = name[0]
    for char in name[1:]:
        for key in mapping:
            if char in key:
                code = mapping[key]
                if code != result[-1]:
                    result += code

    return (result + "000")[:4]


def generate_blocking_tokens(record):

    tokens = []

    if record.get("ssn"):
        tokens.append("SSN_" + record["ssn"])

    if record.get("phone"):
        tokens.append("PHONE_" + record["phone"])

    if record.get("last_name"):
        tokens.append("LN_" + soundex(record["last_name"]))

    if record.get("address"):
        tokens.append("ADDR_" + record["address"][:10])

    return tokens
