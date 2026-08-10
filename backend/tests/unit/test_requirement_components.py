from app.services.requirement_components import split_requirement_components


def test_splits_compound_requirement_conservatively() -> None:
    assert split_requirement_components("Angular und TypeScript sowie Java") == [
        "Angular", "TypeScript", "Java"
    ]


def test_keeps_single_requirement() -> None:
    assert split_requirement_components("Erfahrung mit automatisierten Tests") == [
        "Erfahrung mit automatisierten Tests"
    ]
