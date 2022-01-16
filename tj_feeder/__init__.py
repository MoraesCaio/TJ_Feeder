"""TJ Feed module
"""

from pathlib import Path
from typing import Union

T_NUMBER = Union[int, float]
T_PATH = Union[Path, str]
T_LOG_LEVEL = Union[int, str]
CFG_FILE = Path(__file__).parent / "data" / "cfg.json"
HEADERS = {
    "duration_mode": [
        "time_spent",
        "issue_name",
        "issue_description",
    ],
    "schedule_mode": [
        "start_time",
        "end_time",
        "issue_name",
        "issue_description",
    ],
}
