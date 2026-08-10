"""Small, conservative decomposition for compound requirements."""

import re


def split_requirement_components(requirement: str) -> list[str]:
    parts = re.split(r"\s+(?:und|sowie|and|as well as)\s+|\s*[;,]\s*", requirement, flags=re.IGNORECASE)
    components = [part.strip(" .:") for part in parts if len(part.strip(" .:")) >= 3]
    return components or [requirement.strip()]
