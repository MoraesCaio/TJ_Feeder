import json

from tj_feeder import CFG_FILE


def load(cfg_file: str = CFG_FILE) -> dict:
    """Loads default settings

    Returns:
        dict: Default settings
    """
    with open(CFG_FILE, 'r') as cfg_file:
        settings = json.load(cfg_file)

    return settings


def save(cfg_dict: dict, cfg_file: str = CFG_FILE) -> None:
    print(f'Saving default settings...')
    with open(cfg_file, 'w') as cfg_json:
        json.dump(cfg_dict, cfg_json, indent=4)
