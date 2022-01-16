"""Implements function for batch execution (per month)
"""

import re
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Optional, Union

import fire
from loguru import logger

from tj_feeder import CFG_FILE, HEADERS, T_PATH, configs
from tj_feeder.time_helper import MONDAY, Dates, WorkDay


class Batch:
    """Create and consume month CSV directories"""

    def __init__(self, cfg_file: Union[Path, str] = CFG_FILE) -> None:
        """Constructor
        dates (timehelper.Dates): Dates object with date utils (e.g.
            current holidays list)
        """
        self.dates = Dates()
        if not Path(cfg_file).exists():
            raise FileNotFoundError(f"File {cfg_file} not found.")
        self.cfg = configs.load(cfg_file)

    def create_month_csv_dir(
        self,
        directory: T_PATH,
        year: int,
        month: int,
        time_mode: Optional[str] = None,
    ) -> None:
        """Creates empty CSV files (i.e. with columns only) regarding holidays
            and weekends.

        Args:
            directory (T_PATH): Path to root directory
            year (int): Year of the CSV files
            month (int): Month of the CSV files
            time_mode (Optional[str]): Either 'schedule_mode' (expects
                'time_start' and 'time_end' columns) or 'duration_mode'
                (expects 'time_spent' column). Defaults to None.
        """
        directory = Path(directory) / f"{year}-{month}"
        directory.mkdir(parents=True, exist_ok=True)

        if time_mode is None:
            time_mode = self.cfg["time_mode"]

        header_line = ",".join(HEADERS[time_mode])
        workdays = self.dates.get_month_workdays(year=year, month=month)

        for workday in workdays:
            csv_path = directory / f"{workday.strftime('%Y-%m-%d')}.csv"
            if not csv_path.is_file():
                with csv_path.open(mode="w") as file:
                    file.write(f"{header_line}\n")

    @staticmethod
    def feed_month_csv_dir(month_directory: T_PATH) -> Optional[str]:
        """feed

        Args:
            month_directory (str): month directory

        Returns:
            str: output string
        """
        # fetching files
        month_directory = Path(month_directory)
        if not month_directory.exists():
            logger.warning(
                f"{month_directory} not found! Halting the process."
            )
            return None

        files = [Path(file) for file in glob(f'{month_directory / "*.csv"}')]
        logger.trace(f"month_directory: {month_directory}")
        logger.trace(f"Files found: {list(map(str, files))}")

        output_str = ""
        last_seen_weekday = MONDAY
        for file in files:
            logger.trace(f"Parsing file {file}")
            try:
                work_day = WorkDay(csv_file=file)
            except ValueError as error:
                logger.warning(f"Skipping {error}")
                continue

            # parsing date
            year, month, day = map(int, re.split(r"\D", file.stem))
            current_day = datetime(year, month, day)
            current_weekday = current_day.weekday()

            # building feed strings
            warning_msg = work_day.issue_warnings()

            daily_feed_str = "\n" * (
                3 if current_weekday < last_seen_weekday else 1
            )
            if warning_msg:
                daily_feed_str += f"# {warning_msg}\n"
            daily_feed_str += work_day.daily_feed(
                year=year, month=month, day=day
            )

            output_str += daily_feed_str

            # updating weekday
            last_seen_weekday = current_weekday

        return output_str


if __name__ == "__main__":
    fire.Fire(Batch)
