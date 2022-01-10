"""Module to load and save the config json file."""

import json

from tj_feeder import CFG_FILE, T_PATH


def load(cfg_file: T_PATH = CFG_FILE) -> dict:
    """Loads default settings

    Args:
        cfg_file (T_PATH, optional): Path to config json file. Defaults to
            CFG_FILE.

    Returns: dict: Default settings
    """
    with open(cfg_file, "r") as configs:
        settings = json.load(configs)

    return settings


def save(cfg_dict: dict, cfg_file: T_PATH = CFG_FILE) -> None:
    """Save config json file

    Args:
        cfg_dict (dict): Dictionary with new default settings
        cfg_file (T_PATH, optional): Path to config json file. Defaults to
            CFG_FILE.
    """
    print("Saving default settings...")
    with open(cfg_file, "w") as cfg_json:
        json.dump(cfg_dict, cfg_json, indent=4)
