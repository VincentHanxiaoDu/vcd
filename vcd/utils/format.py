import re


def _to_snake_case(string: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", string).lower()


def to_snake_case(json_obj) -> str:
    if isinstance(json_obj, dict):
        return {_to_snake_case(k): to_snake_case(v) for k, v in json_obj.items()}
    elif isinstance(json_obj, list):
        return [to_snake_case(v) for v in json_obj]
    else:
        return json_obj
