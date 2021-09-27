# TJ Feeder

This package generates a daily input for [TaskJuggler](https://taskjuggler.org/) from a CSV file (comma as separator) with headers: time_spent (XYmin or X.Yh), issue_name (name of task), and issue_description (optional description of task).

# Installation

The project is available on PyPI's page [TJ_Feeder](https://pypi.org/project/tj-feeder/). To install it, run:

```shell
pip install tj_feeder
```

# Set up

First, you need to set up the starting hour of your shift, the shift duration in hours, and the display mode for task durations (minutes or hours).

You will need a holidays file containing specifying holiday dates in the format **yyyy-mm-dd** (e.g. "2021-25-12"). Make sure to have only one date per line. To set the path to this file, run the command:
```shell
tj_feed define --holidays-file [path_to_file]
```

To set the starting hour of your shift, run the command:
```shell
tj_feed define --starting-hour [integer]
```

To set the shift duration, run the command:
```shell
tj_feed define --shift-hours [integer]
```

To set month starting workday ranging from 1 to 31 (i.e. the first workday accounted for the month's invoice), run the command:

```shell
tj_feed define --month-start-workday [integer]
```

To set the display mode for minutes (in case you want the display mode for hours, you can set this to False), run the command:
```shell
tj_feed define --use-minutes [True|False]
```

# Generating Daily Feed

Create your CSV file following the format **yyyy-mm-dd.csv** (e.g. 2021-09-30.csv) and fill it like this:

```
time_spent,issue_name,issue_description
<time_spent_in_minutes_or_hours>,<issue1_name>,<issue1_description>
<time_spent_in_minutes_or_hours>,<issue2_name>,<issue2_description>
<time_spent_in_minutes_or_hours>,<issue3_name>,<issue3_description>
```

- Make sure to use the same headers;
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
tj_feed feed <your_file.csv>
```

E.g.

```shell
tj_feed feed ../test/2021-09-30.csv
booking communication_9                2021-09-10-09:00 +0.5h                # Meetings
booking management_6                   2021-09-10-09:30 +0.5h                # Weekly review
booking my_proj_13                     2021-09-10-10:00 +7.0h                # Module implementation
```

In case, the time spent is higher than the shift duration the overtime flag will be set automatically.


E.g. (assuming a shift of 8 hours long)

```shell
tj_feed feed ../test/2021-09-30.csv
booking communication_9                2021-09-30-09:00 +0.5h                # Meetings
booking management_6                   2021-09-30-09:30 +0.5h                # Weekly review
booking my_proj_13                     2021-09-30-10:00 +7.5h   {overtime 1} # Module implementation
```

# Batch processing

It's also possible to create and feed multiple CSV files in one go.

## Creating all month's CSV files

To create all necessary CSV files with headers and considering holidays (see: [Set up](#Set-up)) and weekends, run the following command:

```shell
tj_feed create_month_dir --root-directory <path to directory> --year <integer> --month <integer>
```

E.g. running this command "`tj_feed create_month_dir --root-directory my_bookings/ --year 2022 --month 1`", will result in the following structure:
```
root_directory/
|__ 2022-01/
    |__ 2022-01-03.csv
    |__ 2022-01-04.csv
    ...
    |__ 2022-01-31.csv
```

## Feed all month's CSV files

To generate a feed using the month directory created by
"`tj_feed create_month_dir`" command, you can use the
"`tj_feed feed_month_dir`" command.

```shell
tj_feed feed_month_dir --month-directory <path to directory>
```

The feed will have one extra line break to separate bookings per day
and three extra line breaks to separate bookings per week.

E.g. running the command "`tj_feed feed_month_dir --month-directory my_bookings/2022-01`", will have an output similar to this:

```
{bookings for 2022-01-03}

{bookings for 2022-01-04}

{bookings for 2022-01-05}

{bookings for 2022-01-06}

{bookings for 2022-01-07}



{bookings for 2022-01-10}

{bookings for 2022-01-11}

{bookings for 2022-01-12}

...
```
