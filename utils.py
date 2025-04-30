def success(x: dict) -> dict:
    return {"success": True, "result": x}


def failure(error_message: str) -> dict:
    return {"success": False, "error": error_message}
