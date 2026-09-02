from app.schemas.profile import ReferenceUpdate
from app.services.profile_service import RESOURCES, _clean_values


def test_reference_linkedin_url_is_normalized_for_database_storage() -> None:
    payload = ReferenceUpdate(linkedin_url="https://www.linkedin.com/in/maria-mustermann")

    values, _, _ = _clean_values(payload, RESOURCES["references"].fields)

    assert values["linkedin_url"] == "https://www.linkedin.com/in/maria-mustermann"
