def _matching_open_parenthesis(title):
    depth = 0
    for index in range(len(title) - 1, -1, -1):
        char = title[index]
        if char == ')':
            depth += 1
        elif char == '(':
            depth -= 1
            if depth == 0:
                return index
    return None


def clean_db_title(title):
    cleaned = title.rstrip()
    while cleaned.endswith(')'):
        group_start = _matching_open_parenthesis(cleaned)
        if group_start is None:
            cleaned = cleaned[:-1].rstrip()
            continue
        cleaned = cleaned[:group_start].rstrip()
    return cleaned
