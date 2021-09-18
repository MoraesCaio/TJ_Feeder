from datetime import datetime, timedelta
import math
import re

import fire
from loguru import logger
import pandas as pd


FLOAT_PATTERN = r"[+]?(\d+(\.\d*)?|\.\d+)"


def __parse_time(time_str):
    if not re.fullmatch(FLOAT_PATTERN + r'(min|h)', time_str):
        raise ValueError(f'Invalid period found: {time_str}. '
                         f'Please inform with either of these formats: '
                         f'XYmin; X.Yh'
                         )

    if 'h' in time_str:
        hours = float(time_str.replace('h', ''))
        minutes = round(hours * 60)
    else:
        minutes = int(time_str.replace('+', '').replace('min', ''))
        hours = round(minutes / 60, 2)

    return minutes, hours


def feed(hours_csv, day=1, month=1, year=2021, starting_hour=9, shift_hours=8, use_minutes=False):
    df = pd.read_csv(hours_csv)
    minute_hour_times = [__parse_time(ts) for ts in df['time_spent']]
    minutes_per_day, hours_per_day = list(map(list, zip(*minute_hour_times)))

    total_worktime = sum(minutes_per_day)
    expected_worktime = shift_hours * 60
    overtime = max(0, total_worktime - expected_worktime)
    # due_time = min(expected_worktime - total_worktime, expected_worktime)

    cur_time = datetime(year, month, day, starting_hour)
    for i in range(len(df)):
        fmt_time = cur_time.strftime('%Y-%m-%d-%H:%M')
        spent_time = f'+{minutes_per_day[i]}min' if use_minutes else f'+{hours_per_day[i]}h'
        if overtime and i == len(df) - 1:
            spent_time += ' {overtime 1}'
        print(f"booking {df['issue_name'].iloc[i]:30} {fmt_time} {spent_time:20} # {df['issue_description'].iloc[i]}")
        cur_time += timedelta(minutes=minutes_per_day[i])

    # logger.info(f'\n{df}')
    # logger.info(f'\n{minutes_per_day}')


@logger.catch(reraise=True)
def main():
    fire.Fire(feed)


if __name__ == "__main__":
    main()
