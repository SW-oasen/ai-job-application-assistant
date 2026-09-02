from app.core.config import get_settings
from app.core.demo_mode import validate_demo_database

validate_demo_database(get_settings())
