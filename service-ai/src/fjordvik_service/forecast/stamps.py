"""What every phase 2 result names (G10, W8). The code moved to fjordvik_service.common.stamps
in phase 3; these names stay, with phase 2's model version and libraries, so its imports,
tests and results don't change."""

from ..common import stamps as _common
from ..common.stamps import (  # noqa: F401  (re-exported for phase 2)
    STAMP_FIELDS, data_checksum, git_commit, scores_sha256, sha256_file, sha256_json, uncommitted)
from . import DATA_BASIS, MODEL_VERSION

LIBRARIES = ["numpy", "pandas", "scipy", "statsmodels", "patsy"]


def environment():
    """The exact Python and phase 2 library versions behind a result."""
    return _common.environment(LIBRARIES)


def stamp(data_dir, commit):
    return _common.stamp(data_dir, commit, MODEL_VERSION, DATA_BASIS)
