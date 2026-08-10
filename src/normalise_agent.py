def normalise_service(raw: str) -> str:
    return raw.strip().lower()


def normalise_level(raw: str) -> str:
    val = raw.strip().upper() if raw else ""
    return val or "UNKNOWN"
