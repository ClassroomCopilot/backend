import modules.database.schemas.calendar_neo as neo_calendar
from modules.database.tools.neontology.baserelationship import BaseRelationship
from typing import ClassVar

## Calendar layer relationships
class CalendarIncludesYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'CALENDAR_INCLUDES_YEAR'
    source: neo_calendar.CalendarNode
    target: neo_calendar.CalendarYearNode

class YearIncludesMonth(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_INCLUDES_MONTH'
    source: neo_calendar.CalendarYearNode
    target: neo_calendar.CalendarMonthNode

class YearIncludesWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_INCLUDES_WEEK'
    source: neo_calendar.CalendarYearNode
    target: neo_calendar.CalendarWeekNode
    
class MonthIncludesDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'MONTH_INCLUDES_DAY'
    source: neo_calendar.CalendarMonthNode
    target: neo_calendar.CalendarDayNode
    
class WeekIncludesDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'WEEK_INCLUDES_DAY'
    source: neo_calendar.CalendarWeekNode
    target: neo_calendar.CalendarDayNode

# Sequenced Relationships for Calendar
class YearFollowsYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_FOLLOWS_YEAR'
    source: neo_calendar.CalendarYearNode
    target: neo_calendar.CalendarYearNode

class MonthFollowsMonth(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'MONTH_FOLLOWS_MONTH'
    source: neo_calendar.CalendarMonthNode
    target: neo_calendar.CalendarMonthNode

class WeekFollowsWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'WEEK_FOLLOWS_WEEK'
    source: neo_calendar.CalendarWeekNode
    target: neo_calendar.CalendarWeekNode

class DayFollowsDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'DAY_FOLLOWS_DAY'
    source: neo_calendar.CalendarDayNode
    target: neo_calendar.CalendarDayNode
