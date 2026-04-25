import re
from datetime import datetime
from hashing import generate_blocking_tokens

def normalize_record(record):

    record["first_name"] = normalize_name(record.get("first_name"))
    record["last_name"] = normalize_name(record.get("last_name"))
    record["address"] = normalize_address(record.get("address"))
    record["phone"] = normalize_phone(record.get("phone"))
    record["ssn"] = normalize_ssn(record.get("ssn"))
    record["email"] = normalize_email(record.get("email"))
    record["dob"] = normalize_dob(record.get("dob"))

    record["blocking_tokens"] = generate_blocking_tokens(record)

    return record


def normalize_name(name):
    if not name:
        return None
    return name.lower().strip()


def normalize_address(address):
    if not address:
        return None

    address = address.lower()
    address = re.sub(r"[^\w\s]", "", address)

    mapping = {
        "st": "street",
        "rd": "road",
        "ave": "avenue",
        "blvd": "boulevard"
    }

    tokens = address.split()
    tokens = [mapping.get(t, t) for t in tokens]

    return " ".join(tokens)


def normalize_phone(phone):
    if not phone:
        return None

    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        digits = "1" + digits

    return digits


def normalize_ssn(ssn):
    if not ssn:
        return None

    return re.sub(r"\D", "", ssn)


def normalize_email(email):
    if not email:
        return None
    return email.lower().strip()


def normalize_dob(dob):
    if not dob:
        return None

    try:
        return datetime.strptime(dob, "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return dob
