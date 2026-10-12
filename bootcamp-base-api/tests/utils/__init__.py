from os import environ

from tests.utils.db_utils import DbUtils
from tests.utils.random_generator import RandomGenerator


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")
