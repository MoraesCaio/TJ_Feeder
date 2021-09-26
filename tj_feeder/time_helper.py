from datetime import timedelta, datetime
from typing import List, Optional, Tuple, Callable
import re

import fire
from loguru import logger
import pandas as pd

from tj_feeder import CFG_FILE, HEADERS, configs


SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * 60
MONDAY = 0
SATURDAY = 5
SUNDAY = 6
FLOAT_PATTERN = r"[+]?(\d+(\.\d*)?|\.\d+)"


def td_minutes(td: timedelta) -> int:
    return td.total_seconds() // SECONDS_PER_MINUTE


def td_hours(td: timedelta) -> float:
    return td.total_seconds() / SECONDS_PER_HOUR


def parse_time_string(time: str) -> Tuple[int, float]:
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


class Dates:
    cfg = configs.load()

    def __init__(self):
        try:
            self.holidays_file = self.cfg['holidays_file']
        except KeyError as e:
            raise KeyError('Please set the path to holidays_file with "tj_feed define --holidays-file <path_to_holiday_file>"') from e
        self.holidays = Dates.parse_holidays_file(self.holidays_file)

    @staticmethod
    def parse_holidays_file(holidays_file: str) -> List[Optional[datetime]]:
        """Search for dates in the lines of a file following the format "YYYY-MM-DD" (separator can be any non-digit character).

        Args:
            holidays_file (str): Path to holidays file

        Returns:
            List[Optional[datetime]]: Holidays found in file
        """
        found_dates = []
        with open(holidays_file) as file:
            for line in file:
                match = re.search(r'\d{4}\D\d{2}\D\d{2}', line)
                if match:
                    match_str = match.group(0)
                    formatted = re.sub(r'\D', '-', match_str)
                    found_dates.append(datetime.strptime(formatted, '%Y-%m-%d'))

        return found_dates

    @staticmethod
    def is_weekend(date: datetime) -> bool:
        """Checks if the date is a weekend

        Args:
            date (datetime): Date to check

        Returns:
            bool: Returns True if the day is either saturday or sunday; False, otherwise.
        """
        return date.weekday() in [SATURDAY, SUNDAY]

    @staticmethod
    def is_next_month(date: datetime, month: int) -> bool:
        """Checks if the date is the initial date of the next month.

        Args:
            date (datetime): Date to check
            month (int): Current month

        Returns:
            bool: True if is the date is the first date of the next month. False, otherwise.
        """
        return date.day == Dates.cfg['month_start_workday'] and date.month != month

    def get_list_of_days(self, stop_function: Callable, year: int, month: int, start_workday: int) -> List[Optional[datetime]]:
        """Gets a list of workdays considering the holidays using a function
            to detect the end of the list (non-inclusive).

        Args:
            stop_function (Callable): Function that returns True for the first date not to be included.
            year (int): Current year
            month (int): Current month
            week_start_workday (int): First workday of the period ranging from 1 to 31.

        Returns:
            List[Optional[datetime]]: [description]
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
            if current_dt in self.holidays \
                or self.is_weekend(current_dt):
                current_dt += day_td
                continue

            # workday
            workdays.append(current_dt)
            current_dt += day_td

        return workdays

    def get_week_workdays(self, year: int, month: int, week_start_workday: int) -> List[Optional[datetime]]:
        """Gets a list of workdays for the week considering the holidays.

        Args:
            year (int): Current year
            month (int): Current month
            week_start_workday (int): First workday of the week. Usually, the date for monday.

        Returns:
            List[Optional[datetime]]: Week's workday dates
        """
        return self.get_list_of_days(
            stop_function=self.is_weekend,
            year=year,
            month=month,
            start_workday=week_start_workday
        )

    def get_month_workdays(self, year: int, month: int) -> List[Optional[datetime]]:
        """Gets a list of workdays for the month considering the holidays.

        Args:
            year (int): Current year
            month (int): Current month

        Returns:
            List[Optional[datetime]]: month's workday dates
        """
        return self.get_list_of_days(
            stop_function=lambda dt: Dates.is_next_month(dt, month),
            year=year,
            month=month,
            start_workday=Dates.cfg['month_start_workday']
        )


class WorkDay:

    def __init__(self, csv_file: str, cfg_file: str = CFG_FILE):
        self.cfg = configs.load(cfg_file=cfg_file)

        self.df = pd.read_csv(csv_file).sort_values(HEADERS[1])

        found_headers = self.df.columns.to_list()
        if found_headers != HEADERS:
            raise ValueError(f'Wrong headers for: "{csv_file}"\n' + \
                             f'Expected headers: {HEADERS}\n' + \
                             f'Found headers: {found_headers}')

        if not len(self.df.values):
            raise ValueError(f'"{csv_file}" is empty.')

        self.minutes_per_day, self.hours_per_day = WorkDay.parse_time_spent(self.df['time_spent'])

        self.worktime_minutes = sum(self.minutes_per_day)
        self.expected_worktime_minutes = self.cfg['shift_hours'] * 60

        self.due_time_td = WorkDay.calculate_due_time(self.expected_worktime_minutes, self.worktime_minutes)
        self.over_time_td = WorkDay.calculate_over_time(self.expected_worktime_minutes, self.worktime_minutes)

    @staticmethod
    def parse_time_spent(time_spent: pd.Series) -> Tuple[List[int], List[int]]:
        minute_hour_times = [parse_time_string(ts) for ts in time_spent]
        minutes_per_day, hours_per_day = tuple(map(list, zip(*minute_hour_times)))
        return minutes_per_day, hours_per_day

    @staticmethod
    def calculate_over_time(expected_worktime_minutes: int, worktime_minutes: int) -> timedelta:
        return timedelta(minutes=max(0, worktime_minutes - expected_worktime_minutes))

    @staticmethod
    def calculate_due_time(expected_worktime_minutes: int, worktime_minutes: int) -> timedelta:
        return timedelta(minutes=min(expected_worktime_minutes - worktime_minutes, expected_worktime_minutes))

    def daily_feed(self, year, month, day):
        daily_feed_str = ''

        # units
        if self.cfg['use_minutes']:
            value_per_day = self.minutes_per_day
            UNIT = 'min'
        else:
            value_per_day = self.hours_per_day
            UNIT = 'h'

        # main loop
        SHIFT_TD = timedelta(hours=self.cfg['shift_hours'])
        cummulative_td = timedelta(minutes=0)
        cur_dt = datetime(year, month, day, self.cfg['starting_hour'])
        for i in range(len(self.minutes_per_day)):
            fmt_time = cur_dt.strftime('%Y-%m-%d-%H:%M')

            # spent time
            spent_time = f'+{value_per_day[i]}{UNIT}'

            # over time
            cummulative_td += timedelta(minutes=self.minutes_per_day[i])
            if cummulative_td > SHIFT_TD:
                spent_time = f'{spent_time:7} {{over_time 1}}'

            # feed line
            daily_feed_str += f"booking {self.df['issue_name'].iloc[i]:30} " + \
                              f"{fmt_time} {spent_time:20} " + \
                              f"# {self.df['issue_description'].iloc[i]}\n"

            # next datetime to show
            cur_dt += timedelta(minutes=self.minutes_per_day[i])

        return daily_feed_str

    def issue_warnings(self) -> str:
        logger.info('Checking missing time and over time...')
        logger.info(f'work_time {self.worktime_minutes:3} minutes')

        warning_msg = ''
        if td_minutes(self.due_time_td):
            warning_msg = f"You are missing {td_hours(self.due_time_td):.2f} hours ({td_minutes(self.due_time_td)} minutes)"
        elif td_minutes(self.over_time_td):
            warning_msg = f"You've worked overtime of {td_hours(self.over_time_td):.2f} hours ({td_minutes(self.over_time_td)} minutes)"

        logger.warning(warning_msg)

        return warning_msg


if __name__ == "__main__":
    fire.Fire()
