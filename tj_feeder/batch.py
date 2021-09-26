from datetime import datetime
from pathlib import Path
from glob import glob
import re

import fire

from tj_feeder import HEADERS
from tj_feeder.time_helper import Dates, WorkDay, MONDAY


class Batch:

    def __init__(self):
        self.dates = Dates()

    def create_month_csv_dir(self, directory: str, year: int, month: int) -> None:
        directory = Path(directory) / f'{year}-{month}'
        directory.mkdir(parents=True, exist_ok=True)

        header_line = ','.join(HEADERS)
        workdays = self.dates.get_month_workdays(year=year, month=month)

        for workday in workdays:
            csv_path = directory / f"{workday.strftime('%Y-%m-%d')}.csv"
            if not csv_path.is_file():
                with csv_path.open(mode='w') as file:
                    file.write(f'{header_line}\n')

    def feed_month_csv_dir(self, month_directory: str) -> str:
        # fetching files
        month_directory = Path(month_directory)
        files = [Path(file) for file in glob(f'{month_directory / "*.csv"}')]

        output_str = ''
        last_seen_weekday = MONDAY
        for file in files:
            try:
                work_day = WorkDay(csv_file=file)
            except ValueError as e:
                continue

            # parsing date
            year, month, day = map(int, re.split(r'\D', file.stem))
            current_day = datetime(year, month, day)
            current_weekday = current_day.weekday()

            # building feed strings
            warning_msg = work_day.issue_warnings()

            daily_feed_str = '\n' * (3 if current_weekday < last_seen_weekday else 1)
            if warning_msg:
                daily_feed_str += f'# {warning_msg}\n'
            daily_feed_str += work_day.daily_feed(year=year, month=month, day=day)

            output_str += daily_feed_str

            # updating weekday
            last_seen_weekday = current_weekday

        return output_str


if __name__ == "__main__":
    fire.Fire(Batch)
