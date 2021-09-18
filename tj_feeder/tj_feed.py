from datetime import datetime, timedelta
import re
from typing import Tuple

import fire
from loguru import logger
import pandas as pd


FLOAT_PATTERN = r"[+]?(\d+(\.\d*)?|\.\d+)"


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


def feed(
    csv_file: str,
    day: int = 1,
    month: int = 1,
    year: int = 2021,
    starting_hour: int = 9,
    shift_hours: int = 8,
    use_minutes: bool = False
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
    df = pd.read_csv(csv_file)

    # parsing time
    minute_hour_times = [__parse_time(ts) for ts in df['time_spent']]
    minutes_per_day, hours_per_day = list(map(list, zip(*minute_hour_times)))

    # calculating
    total_worktime = sum(minutes_per_day)
    expected_worktime = shift_hours * 60
    overtime = max(0, total_worktime - expected_worktime)
    due_time = min(expected_worktime - total_worktime, expected_worktime)

    # building daily feed
    daily_feed_str = ''
    cur_time = datetime(year, month, day, starting_hour)
    for i in range(len(df)):
        fmt_time = cur_time.strftime('%Y-%m-%d-%H:%M')

        # spent time
        spent_time = f'+{minutes_per_day[i]}min' if use_minutes else f'+{hours_per_day[i]}h'
        if overtime and i == len(df) - 1:
            spent_time = f'{spent_time:7} {{overtime 1}}'

        # feed line
        daily_feed_str += f"booking {df['issue_name'].iloc[i]:30} " + \
                      f"{fmt_time} {spent_time:20} " + \
                      f"# {df['issue_description'].iloc[i]}\n"

        cur_time += timedelta(minutes=minutes_per_day[i])

    return daily_feed_str


@logger.catch(reraise=True)
def main():
    fire.Fire(feed)


if __name__ == "__main__":
    main()
