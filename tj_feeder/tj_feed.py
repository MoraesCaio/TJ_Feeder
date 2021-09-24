from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from typing import Dict, Optional, Tuple, Union

import fire
from loguru import logger
import pandas as pd


FLOAT_PATTERN = r"[+]?(\d+(\.\d*)?|\.\d+)"
CFG_FILE = Path(__file__).parent / 'data' / 'cfg.json'


def __parse_time(time: str) -> Tuple[int, float]:
    """Considering the following formats: 30min and 0.5h (a preceding '+' symbol is optional).
    Converts the input from one of those formats to the other.

    Args:
        time (str): Time string

    Raises:
        ValueError: Raised if the input is in neither of the formats

    Returns:
        Tuple[int, float]: Tuple with both formats: (minutes, hours)
    """
    if not re.fullmatch(FLOAT_PATTERN + r'(min|h)', time):
        raise ValueError(f'Invalid period found: {time}. '
                         f'Please inform with either of these formats: '
                         f'XYmin; X.Yh')

    if 'h' in time:
        hours = float(time.replace('h', ''))
        minutes = round(hours * 60)
    else:
        minutes = int(time.replace('+', '').replace('min', ''))
        hours = round(minutes / 60, 2)

    return minutes, hours


def __load_default_settings() -> Dict[str, Union[int, bool]]:
    """Loads default settings

    Returns:
        Dict[str, Union[int, bool]]: Default settings
    """
    with open(CFG_FILE, 'r') as cfg_file:
        default_settings = json.load(cfg_file)

    return default_settings


def define_default(
    starting_hour: Optional[int] = None,
    shift_hours: Optional[int] = None,
    use_minutes: Optional[bool] = None
) -> None:
    """Sets default configuration.

    Args:
        starting_hour (int, optional): Starting hour of the shift. Defaults to None.
        shift_hours (int, optional): How long is the shift in hours. Defaults to None.
        use_minutes (bool, optional): If True, the feed periods will be in minutes; if False, the periods will be in hours. Defaults to None.
    """

    cfg_dict = __load_default_settings()
    if starting_hour is not None:
        print(f'Defining starting hour as {starting_hour}')
        cfg_dict['starting_hour'] = starting_hour

    if shift_hours is not None:
        print(f'Defining shift duration as {shift_hours} hours')
        cfg_dict['shift_hours'] = shift_hours

    if use_minutes is not None:
        print(f'Defining duration unit as {"minutes" if use_minutes else "hours"}')
        cfg_dict['use_minutes'] = use_minutes

    print(f'Saving default settings...')
    with open(CFG_FILE, 'w') as cfg_json:
        json.dump(cfg_dict, cfg_json, indent=4)


def feed(
    csv_file: str,
    day: int = 1,
    month: int = 1,
    year: int = 2021,
) -> str:
    """Generates a Daily feed for TaskJuggler from a csv file.

    Args:
        csv_file (str): Path to csv file.
        day (int, optional): Day of entry. Defaults to 1.
        month (int, optional): Month of entry. Defaults to 1.
        year (int, optional): Year of entry. Defaults to 2021.
        starting_hour (int, optional): Starting hour of the shift. Defaults to 9.
        shift_hours (int, optional): How long is the shift in hours. Defaults to 8.
        use_minutes (bool, optional): If True, the feed periods will be in minutes; if False, the periods will be in hours. Defaults to False.

    Returns:
        str: Daily feed string
    """
    # loading default settings
    default_settings_dict = __load_default_settings()
    starting_hour = default_settings_dict['starting_hour']
    shift_hours = default_settings_dict['shift_hours']
    use_minutes = default_settings_dict['use_minutes']

    # loading hours
    df = pd.read_csv(csv_file)

    # parsing time
    minute_hour_times = [__parse_time(ts) for ts in df['time_spent']]
    minutes_per_day, hours_per_day = list(map(list, zip(*minute_hour_times)))

    # calculating
    total_worktime = sum(minutes_per_day)
    expected_worktime = shift_hours * 60
    over_time = timedelta(minutes=max(0, total_worktime - expected_worktime))
    due_time = timedelta(minutes=min(expected_worktime - total_worktime, expected_worktime))
    expected_time = timedelta(minutes=expected_worktime)

    # building daily feed
    daily_feed_str = ''
    cummulative_time = timedelta(minutes=0)
    shift_time = timedelta(hours=shift_hours)
    cur_time = datetime(year, month, day, starting_hour)
    for i in range(len(df)):
        fmt_time = cur_time.strftime('%Y-%m-%d-%H:%M')

        # spent time
        spent_time = f'+{minutes_per_day[i]}min' if use_minutes else f'+{hours_per_day[i]}h'
        cummulative_time += timedelta(minutes=minutes_per_day[i])
        if cummulative_time > shift_time:
            spent_time = f'{spent_time:7} {{over_time 1}}'

        # feed line
        daily_feed_str += f"booking {df['issue_name'].iloc[i]:30} " + \
                          f"{fmt_time} {spent_time:20} " + \
                          f"# {df['issue_description'].iloc[i]}\n"

        cur_time += timedelta(minutes=minutes_per_day[i])

    logger.info('Checking missing time and over time...')
    logger.info(f'work_time {cummulative_time.seconds // 60:3} minutes')
    logger.info(f'over_time {over_time.seconds // 60:3} minutes')
    logger.info(f'due_time  {due_time.seconds // 60:3} minutes')
    if due_time.seconds > 60:
        missing_minutes = due_time.seconds // 60
        missing_hours = missing_minutes / 60
        logger.warning(f"You are missing {missing_hours} hours ({missing_minutes} minutes)")
    elif over_time.seconds > 60:
        extra_minutes = over_time.seconds // 60
        extra_hours = extra_minutes / 60
        logger.warning(f"You worked {extra_hours} hours ({extra_minutes} minutes)")

    return daily_feed_str


@logger.catch(reraise=True)
def main():
    fire.Fire()


if __name__ == "__main__":
    main()
