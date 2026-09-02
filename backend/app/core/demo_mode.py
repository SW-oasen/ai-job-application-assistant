from sqlalchemy.engine import make_url

from app.core.config import Settings


def validate_demo_database(settings: Settings) -> None:
    """Prevent a demo process from connecting to the regular application database."""
    if not settings.demo_mode:
        return
    if not settings.database_url:
        raise RuntimeError("Demo-Modus benötigt DATABASE_URL.")
    database_name = make_url(settings.database_url).database
    if database_name != settings.demo_database_name:
        raise RuntimeError(
            "Demo-Modus verweigert den Start: DATABASE_URL muss auf "
            f"'{settings.demo_database_name}' zeigen."
        )
