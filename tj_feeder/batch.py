from pathlib import Path

import fire
from loguru import logger

from tj_feeder import HEADERS
from tj_feeder.time_helper import Dates


@logger.catch
class Batch:

    def __init__(self, holidays_file: str):
        self.dates = Dates(holidays_file)

    def create_month_csv_dir(self, directory: str, year: int, month: int, month_start_workday: int = 24) -> None:
        directory = Path(directory) / f'{year}-{month}'
        directory.mkdir(parents=True, exist_ok=True)

        header_line = ','.join(HEADERS)
        workdays = self.dates.get_month_workdays(year=year, month=month, month_start_workday=month_start_workday)

        for workday in workdays:
            csv_path = directory / f"{workday.strftime('%Y-%m-%d')}.csv"
            if not csv_path.is_file():
                with csv_path.open(mode='w') as file:
                    file.write(f'{header_line}\n')


if __name__ == "__main__":
    fire.Fire(Batch)
