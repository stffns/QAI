import pytest

# This legacy simulation test targeted a shell-based runner. The project now enforces
# Maven-only execution for Gatling runs, so this suite is deprecated.
pytest.skip("Deprecated: Shell runner simulation retired (Maven-only policy)", allow_module_level=True)
