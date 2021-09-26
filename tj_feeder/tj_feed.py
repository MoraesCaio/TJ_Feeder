from typing import Optional

import fire
from loguru import logger

from tj_feeder import configs, time_helper as th


def define(
    starting_hour: Optional[int] = None,
    shift_hours: Optional[int] = None,
    month_start_workday: Optional[int] = None,
    use_minutes: Optional[bool] = None,
) -> None:
    """Sets default configuration.

    Args:
        starting_hour (int, optional): Starting hour of the shift. Defaults to None.
        shift_hours (int, optional): How long is the shift in hours. Defaults to None.
        use_minutes (bool, optional): If True, the feed periods will be in minutes; if False, the periods will be in hours. Defaults to None.
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

    configs.save(cfg_dict)


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

    Returns:
        str: Daily feed string
    """
    work_day = th.WorkDay(csv_file=csv_file)
    daily_feed_str = work_day.daily_feed(year=year, month=month, day=day)
    work_day.issue_warnings()

    return daily_feed_str


@logger.catch(reraise=True)
def main():
    fire.Fire()


if __name__ == "__main__":
    main()
