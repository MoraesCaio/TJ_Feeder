"""Main module. Contains the endpoints of CLI.
"""
import re
import sys
from pathlib import Path
from typing import Optional, Union

import fire
from loguru import logger

from tj_feeder import HEADERS, T_LOG_LEVEL, T_PATH, configs
from tj_feeder import time_helper as th
from tj_feeder.batch import Batch


class TJFeed:
    """Module interface class"""

    def __init__(self, log_level: Optional[T_LOG_LEVEL]) -> None:
        """Constructor

        Args:
            log_level (Optional[T_LOG_LEVEL]): Loguru level
        """
        if log_level:
            logger.add(sys.stderr, level=log_level)
            logger.remove(0)

    @staticmethod
    def define(
        starting_hour: Optional[int] = None,
        shift_hours: Optional[int] = None,
        month_start_workday: Optional[int] = None,
        use_minutes: Optional[bool] = None,
        holidays_file: Optional[Union[Path, str]] = None,
        time_mode: Optional[str] = None,
    ) -> None:
        """Sets default configuration.

        Args:
            starting_hour (int, optional): Starting hour of the shift.
                Defaults to None.
            shift_hours (int, optional): How long is the shift in hours.
                Defaults to None.
            month_start_workday (int, optional): Starting month workday;
                it ranges from 1 to 31. Defaults to None.
            use_minutes (bool, optional): If True, the feed periods will be in
                minutes; if False, the periods will be in hours.
                    Defaults to None.
            holidays_file (Optional[Union[Path, str]], optional): Path to file
                containing specifying
                holiday dates in the format yyyy-mm-dd (e.g. "2021-25-12")
            time_mode (Optional[str], optional): Set to 'schedule_mode', to
                use 'start_time' and 'end_time' columns. Set to 'duration_mode'
                to use 'time_spent' column. Defaults to None.
        """

        cfg_dict = configs.load()

        if starting_hour is not None:
            if not 0 <= starting_hour <= 23:
                print("Use an integer between 0 and 23 for the starting hour.")

            print(f"Defining starting hour as {starting_hour}")
            cfg_dict["starting_hour"] = starting_hour

        if shift_hours is not None:
            if not 0 <= shift_hours <= 23:
                print("Use an integer between 0 and 23 for the shift hours.")
            print(f"Defining shift duration as {shift_hours} hours")
            cfg_dict["shift_hours"] = shift_hours

        if month_start_workday is not None:
            if not 1 <= month_start_workday <= 31:
                print(
                    "Use an integer between 1 and 31 for the month starting"
                    " workday."
                )
            print(f"Defining starting hour as {month_start_workday}")
            cfg_dict["month_start_workday"] = month_start_workday

        if use_minutes is not None:
            unit_plural = "minutes" if use_minutes else "hours"
            print(f"Defining duration unit as {unit_plural}")
            cfg_dict["use_minutes"] = use_minutes

        if holidays_file is not None:
            print(f"Defining holidays_file as {holidays_file}")
            if not Path(holidays_file).exists():
                print(f"File {holidays_file} not found.")
                return
            cfg_dict["holidays_file"] = holidays_file

        if time_mode is not None:
            if time_mode not in HEADERS:
                allowed_values = "\n\t- ".join(HEADERS)
                print(
                    "Time mode should be one of the following:"
                    f"\n\t- {allowed_values}"
                )
                return
            print(f"Defining time_mode as {time_mode}")
            cfg_dict["time_mode"] = time_mode

        configs.save(cfg_dict)

    @staticmethod
    def feed(csv_file: str) -> str:
        """Generates a Daily feed for TaskJuggler from a csv file.
            File name must follow the format "yyyy-mm-dd.csv"
            (e.g. 2021-09-24.csv)

        Args:
            csv_file (str): Path to csv file.
        Returns:
            str: Daily feed string
        """
        work_day = th.WorkDay(csv_file=csv_file)
        year, month, day = map(int, re.split(r"\D", Path(csv_file).stem))
        daily_feed_str = work_day.daily_feed(year=year, month=month, day=day)
        work_day.issue_warnings()

        return daily_feed_str

    @staticmethod
    def create_month_dir(
        root_directory: str,
        year: int,
        month: int,
        time_mode: Optional[str] = None,
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
            time_mode (Optional[str]): Either 'schedule_mode' (expects
                'time_start' and 'time_end' columns) or 'duration_mode'
                (expects 'time_spent' column). Defaults to None.
        """
        Batch().create_month_csv_dir(root_directory, year, month, time_mode)

    @staticmethod
    def feed_month_dir(month_directory: T_PATH) -> Optional[str]:
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
        logger.trace("Starting the parsing process of a month directory...")
        return Batch().feed_month_csv_dir(month_directory)


@logger.catch(reraise=True)
def main() -> None:
    """Main function. Used to call fire wrapper."""
    fire.Fire(TJFeed)


if __name__ == "__main__":
    main()
