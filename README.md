# TJ Feeder

This package generates a daily input for [TaskJuggler](https://taskjuggler.org/) from a CSV file (comma as separator) with headers: time_spent (XYmin or X.Yh), issue_name (name of task), and issue_description (optional description of task).

# Installation

The project is available on PyPI's page [TJ_Feeder](https://pypi.org/project/tj-feeder/). To install it, run:

```shell
pip install tj_feeder
```

# Set up

First, you need to set up the starting hour of your shift, the shift duration in hours, and the display mode for task durations (minutes or hours).

To set the starting hour, run the command:
```shell
tj_feed define_default --starting-hour [integer]
```

To set the shift duration, run the command:
```shell
tj_feed define_default --shift-hours [integer]
```

To set the display mode for minutes (in case you want the display mode for hours, you can set this to False), run the command:
```shell
tj_feed define_default --use-minutes [True|False]
```

# Generating Daily Feed

Create your CSV file following the format:

```
time_spent,issue_name,issue_description
<time_spent_in_minutes_or_hours>,<issue_name>,<issue_description>
```

- The time spent can be in two formats: XYmin or X.Yh (e.g. 45min or 0.75h);
- Make sure the issue names match with the tasks defined by your team manager;
- The issue description is optional;
- Use commas only to separate the values.

E.g.:
```
time_spent,issue_name,issue_description
30min,communication_9,Meetings
0.5h,management_6,Weekly review
7.0h,my_proj_13,Module implementation
```
Once you have your csv file ready. You can run the following command:
```shell
tj_feed <your_file.csv> --year <entry_year_int> --month <entry_month_int> --day <entry_day_int>
```

E.g.

```shell
tj_feed feed ../test/your_file.csv --day 10 --month 9 --year 2021
booking communication_9                2021-09-10-09:00 +0.5h                # Meetings
booking management_6                   2021-09-10-09:30 +0.5h                # Weekly review
booking my_proj_13                     2021-09-10-10:00 +7.0h                # Module implementation
```

In case, the time spent is higher than the shift duration the overtime flag will be set automatically.


E.g. (assuming a shift of 8 hours long)

```shell
tj_feed feed ../test/your_file.csv --day 10 --month 9 --year 2021
booking communication_9                2021-09-10-09:00 +0.5h                # Meetings
booking management_6                   2021-09-10-09:30 +0.5h                # Weekly review
booking my_proj_13                     2021-09-10-10:00 +7.5h   {overtime 1} # Module implementation
```