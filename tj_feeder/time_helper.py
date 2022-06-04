"""Module to deal with time and day calculations.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Tuple, Union, cast

import fire
import pandas as pd
from loguru import logger

from tj_feeder import CFG_FILE, HEADERS, T_NUMBER, T_PATH, configs

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * 60
MONDAY = 0
SATURDAY = 5
SUNDAY = 6
FLOAT_PATTERN = r"[+]?(\d+(\.\d*)?|\.\d+)"


class Dates:
    """Class to handle calendar days"""

    def __init__(self, cfg_file: Union[Path, str] = CFG_FILE) -> None:
        """Constructor

        Raises:
            KeyError: Raised if holidays file path is not set.
        """
        self.cfg = configs.load(cfg_file)
        try:
            self.holidays_file = self.cfg["holidays_file"]
        except KeyError as error:
            raise KeyError(
                'Please set the path to holidays_file with "tj_feed define'
                ' --holidays-file <path_to_holiday_file>"'
            ) from error
        self.holidays = Dates.parse_holidays_file(self.holidays_file)

    @staticmethod
    def parse_holidays_file(holidays_file: str) -> List[datetime]:
        """Search for dates in the lines of a file following the format
            "YYYY-MM-DD" (separator can be any non-digit character).

        Args:
            holidays_file (str): Path to holidays file

        Returns:
            List[datetime] Holidays found in file
        """
        found_dates = []
        with open(holidays_file) as file:
            for line in file:
                match = re.search(r"\d{4}\D\d{2}\D\d{2}", line)
                if match:
                    match_str = match.group(0)
                    formatted = re.sub(r"\D", "-", match_str)
                    found_dates.append(
                        datetime.strptime(formatted, "%Y-%m-%d")
                    )

        return found_dates

    @staticmethod
    def is_weekend(date: datetime) -> bool:
        """Checks if the date is a weekend

        Args:
            date (datetime): Date to check

        Returns:
            bool: Returns True if the day is either saturday or sunday.
                False, otherwise.
        """
        return date.weekday() in [SATURDAY, SUNDAY]

    @staticmethod
    def is_next_month(date: datetime, month: int) -> bool:
        """Checks if the date is the initial date of the next month.

        Args:
            date (datetime): Date to check
            month (int): Current month

        Returns:
            bool: True if is the date is the first date of the next month.
                False, otherwise.
        """
        return (
            date.day == Dates().cfg["month_start_workday"]
            and date.month != month
        )

    def get_list_of_workdays(
        self,
        stop_function: Callable,
        year: int,
        month: int,
        start_workday: int,
    ) -> List[datetime]:
        """Gets a list of workdays considering the holidays using a function
            to detect the end of the list (non-inclusive).

        Args:
            stop_function (Callable): Function that returns True for the first
                date not to be included.
            year (int): Current year
            month (int): Current month
            week_start_workday (int): First workday of the period ranging from
                1 to 31.

        Returns:
            List[datetime]: List of workdays
        """
        # loop's starting value and increment
        current_dt = datetime(year, month, start_workday)
        day_td = timedelta(days=1)

        workdays = []
        while True:
            # reached end of the week
            if stop_function(current_dt):
                break

            # skipping holidays
            if current_dt in self.holidays or self.is_weekend(current_dt):
                current_dt += day_td
                logger.trace("Skipping day off")
                continue

            # workday
            workdays.append(current_dt)
            current_dt += day_td

        return workdays

    def get_week_workdays(
        self, year: int, month: int, week_start_workday: int
    ) -> List[datetime]:
        """Gets a list of workdays for the week considering the holidays.

        Args:
            year (int): Current year
            month (int): Current month
            week_start_workday (int): First workday of the week. Usually, the
            date for monday.

        Returns:
            List[datetime]: Week's workday dates
        """
        return self.get_list_of_workdays(
            stop_function=self.is_weekend,
            year=year,
            month=month,
            start_workday=week_start_workday,
        )

    def get_month_workdays(self, year: int, month: int) -> List[datetime]:
        """Gets a list of workdays for the month considering the holidays.

        Args:
            year (int): Current year
            month (int): Current month

        Returns:
            List[datetime]: month's workday dates
        """
        return self.get_list_of_workdays(
            stop_function=lambda dt: Dates.is_next_month(dt, month),
            year=year,
            month=month,
            start_workday=Dates().cfg["month_start_workday"],
        )


class WorkDay:
    """Class that encapsulates function regarding time calculation of
    bookings for a given workday.
    """

    # @logger.catch(reraise=True)
    def __init__(self, csv_file: T_PATH, cfg_file: T_PATH = CFG_FILE) -> None:
        """
        Constructor

        Args:
            csv_file (T_PATH): Path to CSV file with booking for a given date
            cfg_file (T_PATH, optional): Path to JSON file with default
                settings. Defaults to CFG_FILE (see `tj_feed define --help`).

        Raises:
            ValueError: Raised if the CSV file contains different headers
            ValueError: Raised if the CSV file does not contain rows
        """
        self.cfg = configs.load(cfg_file=cfg_file)

        self.dataframe = pd.read_csv(csv_file).sort_values("issue_name")

        time_mode = ""
        found_headers = self.dataframe.columns.to_list()
        for time_mode, headers_set in HEADERS.items():
            if set(found_headers) == set(headers_set):
                break
        else:
            # Building string for possible modes:
            #
            # Wrong headers for: "journals/feeds/2021-12/2022-01-21.csv"
            # Expected headers:
            #     - time_spent
            #     - issue_name
            #     - issue_description
            # OR
            #     - start_time
            #     - end_time
            #     - issue_name
            #     - issue_description
            # Found headers: ['time_spent', 'issue_name', 'issue_description']
            expected_headers = "\n\t- " + "\nOR\n\t- ".join(
                [
                    "\n\t- ".join(header_group)
                    for header_group in HEADERS.values()
                ]
            )

            raise ValueError(
                f'Wrong headers for: "{csv_file}"\n'
                f"Expected headers: {expected_headers}\n"
                f"Found headers: {found_headers}"
            )

        if not self.dataframe.values.size:
            raise ValueError(f'"{csv_file}" is empty.')

        self.minutes_per_day, self.hours_per_day = WorkDay.parse_time_spent(
            self.dataframe, time_mode
        )

        self.worktime_minutes = sum(self.minutes_per_day)
        self.expected_worktime_minutes = self.cfg["shift_hours"] * 60

        self.due_time_td = WorkDay.calculate_due_time(
            self.expected_worktime_minutes, self.worktime_minutes
        )
        self.overtime_td = WorkDay.calculate_overtime(
            self.expected_worktime_minutes, self.worktime_minutes
        )

    @staticmethod
    def fmt_time_schedule(time_schedule: str) -> str:
        """Standardize time schedule input to the following format "01:23"
        (i.e. "2-digits:2-digits")

        Args:
            time_schedule (str): A time mark with 3 to 4 digits and an optional
                separator.

        Returns:
            str: Formatted time schedule string
        """
        time_schedule = re.sub(r"\D", "", time_schedule)
        if len(time_schedule) > 4:
            raise ValueError(
                "Invalid time schedule: more than 4 digits"
                f" (got {len(time_schedule)})"
            )
        hours = time_schedule[:2]
        minutes = time_schedule[2:4]
        time_schedule = f"{hours:>02}:{minutes:>02}"
        return time_schedule

    @staticmethod
    def td_minutes(time_delta: timedelta) -> int:
        """Parse timedelta object into minutes (int type)

        Args:
            time_delta (timedelta): Time delta of a booking

        Returns:
            int: Total minutes worked
        """
        return int(time_delta.total_seconds() / SECONDS_PER_MINUTE)

    @staticmethod
    def td_hours(time_delta: timedelta) -> float:
        """Parse timedelta object into a fraction of hours (float type)

        Args:
            time_delta (timedelta): Time delta of a booking

        Returns:
            float: Total hours worked
        """
        return time_delta.total_seconds() / SECONDS_PER_HOUR

    @staticmethod
    def parse_time_durations(
        time_dataframe: pd.DataFrame,
    ) -> List[Tuple[int, float]]:
        """Considering the following formats: 30min and 0.5h (a preceding '+'
            symbol is optional), converts the input from one of those formats
            to the other.

        Args:
            time (str): Time string

        Raises:
            ValueError: Raised if the input is in neither of the formats

        Returns:
            List[Tuple[int, float]]: List of Tuples with both
                formats: (minutes, hours)
        """
        minute_hour_durations = []

        for time in time_dataframe["time_spent"]:
            if not re.fullmatch(FLOAT_PATTERN + r"(min|h)", time):
                raise ValueError(
                    f"Invalid period found: {time}. "
                    f"Please inform with either of these formats: "
                    f"XYmin; X.Yh"
                )

            if "h" in time:
                hours = float(time.replace("h", ""))
                minutes = round(hours * 60)
            else:
                minutes = int(time.replace("+", "").replace("min", ""))
                hours = round(minutes / 60, 2)

            minute_hour_durations.append((minutes, hours))

        return minute_hour_durations

    @staticmethod
    def parse_time_schedules(
        time_dataframe: pd.DataFrame,
    ) -> List[Tuple[int, float]]:
        """Considering the following format: "10:20,12:35", calculate the
        duration and convert into both possible duration formats: total int
        minutes and total float hours.

        E.g.: "10:20,12:35" -> [135], [2.25]

        Args:
            time_dataframe (pd.DataFrame): Dataframe with time_start and
            time_end columns.

        Returns:
            List[Tuple[int, float]]: List of Tuples with both
                formats: (minutes, hours)
        """
        starts = time_dataframe["start_time"].astype("str")
        ends = time_dataframe["end_time"].astype("str")

        minute_hour_durations = []

        for start, end in zip(starts, ends):
            start = datetime.strptime(
                WorkDay.fmt_time_schedule(start.zfill(4)), "%H:%M"
            )
            end = datetime.strptime(
                WorkDay.fmt_time_schedule(end.zfill(4)), "%H:%M"
            )

            duration = end - start

            total_seconds = duration.total_seconds()
            total_minutes = int(total_seconds / 60)
            # TODO get this value 5 (time precision) from tj or user settings
            total_minutes = int(round(total_minutes / 5) * 5)

            minute_hour_durations.append((total_minutes, total_minutes / 60))

        return minute_hour_durations

    @staticmethod
    def parse_time_spent(
        time_dataframe: pd.Series,
        time_mode: str,
    ) -> Tuple[List[T_NUMBER], List[T_NUMBER]]:
        """Parse time worked on each booking into both forms: by minutes and by
            hours

        Args:
            time_dataframe (pd.Series): Series of str durations
                (e.g. XYmin or X.Yh)

        Returns:
            Tuple[List[T_NUMBER], List[T_NUMBER]]: 2-Tuple of lists. First,
            contains integers for the minutes worked. The second contains float
            equivalents for hours worked.
        """
        if time_mode == "schedule_mode":
            minute_hour_durations = WorkDay.parse_time_schedules(
                time_dataframe
            )
        elif time_mode == "duration_mode":
            time_dataframe["time_spent"] = time_dataframe["time_spent"].astype(
                str
            )
            minute_hour_durations = WorkDay.parse_time_durations(
                time_dataframe
            )
        else:
            raise ValueError(f"Uknown time mode (got {time_mode})")

        minutes_per_day, hours_per_day = cast(
            Tuple[List[T_NUMBER], List[T_NUMBER]],
            tuple(map(list, zip(*minute_hour_durations))),
        )
        return minutes_per_day, hours_per_day

    @staticmethod
    def calculate_overtime(
        expected_worktime_minutes: T_NUMBER, worktime_minutes: T_NUMBER
    ) -> timedelta:
        """Calculate due time using the expected shift duration and actual
            worktime.

        Args:
            expected_worktime_minutes (T_NUMBER): Expected worktime in minutes
            worktime_minutes (T_NUMBER): Actual worktime of a given date

        Returns:
            timedelta: Due time for the given date. Negative value indicates
                that there's still time due to work.
        """
        return timedelta(
            minutes=max(
                0, int(worktime_minutes) - int(expected_worktime_minutes)
            )
        )

    @staticmethod
    def calculate_due_time(
        expected_worktime_minutes: T_NUMBER, worktime_minutes: T_NUMBER
    ) -> timedelta:
        """Calculate due time using the expected shift duration and actual
            worktime.

        Args:
            expected_worktime_minutes (T_NUMBER): Expected worktime in minutes
            worktime_minutes (T_NUMBER): Actual worktime of a given date

        Returns:
            timedelta: Due time for the given date. Negative value indicates
                overtime.
        """
        return timedelta(
            minutes=min(
                max(0, int(expected_worktime_minutes) - int(worktime_minutes)),
                int(expected_worktime_minutes),
            )
        )

    def daily_feed(self, year: int, month: int, day: int) -> str:
        """Generate daily feed string containing all bookings for the given
            date

        Args:
            year (int): Year of the daily feed
            month (int): Month of the daily feed
            day (int): Day of the daily feed

        Returns:
            str: Daily feed
        """
        daily_feed_str = ""

        # units
        if self.cfg["use_minutes"]:
            values_per_day = self.minutes_per_day
        else:
            values_per_day = self.hours_per_day

        # main loop
        shift_td = timedelta(hours=self.cfg["shift_hours"])
        cummulative_td = timedelta(minutes=0)
        cur_dt = datetime(year, month, day, self.cfg["starting_hour"])
        for i in range(len(self.minutes_per_day)):
            fmt_time = cur_dt.strftime("%Y-%m-%d-%H:%M")

            # spent time
            if self.cfg["use_minutes"]:
                spent_time = f"+{values_per_day[i]}min"
            else:
                spent_time = f"+{values_per_day[i]:.2f}h"

            # over time
            cummulative_td += timedelta(minutes=self.minutes_per_day[i])
            if cummulative_td > shift_td:
                spent_time = f"{spent_time:7} {{overtime 1}}"

            # feed line
            daily_feed_str += (
                f"booking {self.dataframe['issue_name'].iloc[i]:30} "
                f"{fmt_time} {spent_time:20} "
            )
            description = f'{self.dataframe["issue_description"].iloc[i]}'
            if description != "nan":
                daily_feed_str += f"# {description}\n"
            else:
                daily_feed_str += "\n"

            # next datetime to show
            cur_dt += timedelta(minutes=self.minutes_per_day[i])

        return daily_feed_str

    def issue_warnings(self) -> str:
        """Logs and returns warning message.

        Returns:
            str: Warning message. Defaults to "" (empty string) if no warning
            is needed
        """
        logger.trace("Checking missing time and over time...")
        logger.trace(f"work_time {self.worktime_minutes:3} minutes")

        warning_msg = ""
        if self.td_minutes(self.due_time_td):
            warning_msg = (
                f"You are missing {self.td_hours(self.due_time_td):.2f}"
                f" hours ({self.td_minutes(self.due_time_td)} minutes)"
            )
        elif self.td_minutes(self.overtime_td):
            warning_msg = (
                f"You've worked overtime of "
                f"{self.td_hours(self.overtime_td):.2f} hours "
                f"({self.td_minutes(self.overtime_td)} minutes)"
            )

        if warning_msg:
            logger.warning(warning_msg)

        return warning_msg


if __name__ == "__main__":
    fire.Fire()
