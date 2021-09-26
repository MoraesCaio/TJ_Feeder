from tj_feeder.batch import Batch
from typing import Optional
from pathlib import Path
import re

import fire
from loguru import logger

from tj_feeder import configs, time_helper as th


def define(
    starting_hour: Optional[int] = None,
    shift_hours: Optional[int] = None,
    month_start_workday: Optional[int] = None,
    use_minutes: Optional[bool] = None,
    holidays_file: Optional[str] = None,
) -> None:
    """Sets default configuration.

    Args:
        starting_hour (int, optional): Starting hour of the shift. Defaults to None.
        shift_hours (int, optional): How long is the shift in hours. Defaults to None.
        month_start_workday (int, optional): Starting month workday; it ranges from 1 to 31. Defaults to None.
        use_minutes (bool, optional): If True, the feed periods will be in minutes; if False, the periods will be in hours. Defaults to None.
        holidays_file (str, optional): Path to file containing specifying holiday dates in the format yyyy-mm-dd (e.g. "2021-25-12")
    """

    cfg_dict = configs.load()

    if starting_hour is not None:
        print(f'Defining starting hour as {starting_hour}')
        cfg_dict['starting_hour'] = starting_hour

    if shift_hours is not None:
        print(f'Defining shift duration as {shift_hours} hours')
        cfg_dict['shift_hours'] = shift_hours

    if month_start_workday is not None:
        print(f'Defining starting hour as {month_start_workday}')
        cfg_dict['month_start_workday'] = month_start_workday

    if use_minutes is not None:
        print(f'Defining duration unit as {"minutes" if use_minutes else "hours"}')
        cfg_dict['use_minutes'] = use_minutes

    if holidays_file is not None:
        print(f'Defining holidays_file as {holidays_file}')
        cfg_dict['holidays_file'] = holidays_file

    configs.save(cfg_dict)


def feed(csv_file: str) -> str:
    """Generates a Daily feed for TaskJuggler from a csv file.
        File name must follow the format "yyyy-mm-dd.csv" (e.g. 2021-09-24.csv)

    Args:
        csv_file (str): Path to csv file.
    Returns:
        str: Daily feed string
    """
    work_day = th.WorkDay(csv_file=csv_file)
    year, month, day = re.split(r'\D', Path(csv_file).stem)
    daily_feed_str = work_day.daily_feed(year=year, month=month, day=day)
    work_day.issue_warnings()

    return daily_feed_str


def create_month_dir(
    root_directory: str,
    year: int,
    month: int
) -> None:
    """Creates all necessary CSV files considering holidays and weekends.

    E.g.:
        root_directory/
        |__ 2022-01/
            |__ 2022-01-03.csv
            |__ 2022-01-04.csv
            ...
            |__ 2022-01-31.csv

    Args:
        root_directory (str): Directory to be created
        year (int): Current year
        month (int): Current month
    """
    Batch().create_month_csv_dir(root_directory, year, month)


def feed_month_dir(month_directory: str) -> str:
    """Generate feed for month directory using one extra line break to
        separate bookings per day and three extra line breaks to
        separate bookings per week.

    E.g.
        2022-01/
            |__ 2022-01-03.csv
            |__ 2022-01-04.csv
            ...
            |__ 2022-01-31.csv

    Output:
        {bookings for 2022-01-03}
        {bookings for 2022-01-04}
        {bookings for 2022-01-05}
        {bookings for 2022-01-06}
        {bookings for 2022-01-07}



        {bookings for 2022-01-10}
        {bookings for 2022-01-11}
        {bookings for 2022-01-12}
        ...

    Args:
        month_directory (str): Month directory to parse

    Returns:
        str: Formatted output for TaskJuggler
    """
    return Batch().feed_month_csv_dir(month_directory)


@logger.catch(reraise=True)
def main():
    fire.Fire()


if __name__ == "__main__":
    main()
