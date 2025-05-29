import json


def wrap_json_lines_as_list(multiline_json: str) -> str:
    """
    Takes newline-delimited JSON objects and returns a JSON array string.
    Raises if any line is invalid JSON.
    """
    json_objects = []
    for line in multiline_json.strip().splitlines():
        if line.strip():  # Skip empty lines
            obj = json.loads(line)
            json_objects.append(obj)
    return json_objects
