import pytest
from seed.seed_data import seed_database


@pytest.fixture(scope="module", autouse=True)
def ensure_clean_seeded_db_per_module():
    """Seeds the database freshly before each test module so tests never bleed state."""
    seed_database()
