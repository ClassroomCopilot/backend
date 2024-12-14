import modules.database.schemas.timetable_neo as neo_timetable
import modules.database.schemas.calendar_neo as neo_calendar
from modules.database.tools.neontology.baserelationship import BaseRelationship
from typing import ClassVar

class CalendarYearIsAcademicYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_ACADEMIC_YEAR'
    source: neo_calendar.CalendarYearNode
    target: neo_timetable.AcademicYearNode
    
class AcademicYearIsCalendarYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_YEAR'
    source: neo_timetable.AcademicYearNode
    target: neo_calendar.CalendarYearNode
    
class CalendarWeekIsAcademicWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_ACADEMIC_WEEK'
    source: neo_calendar.CalendarWeekNode
    target: neo_timetable.AcademicWeekNode
    
class AcademicWeekIsCalendarWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_WEEK'
    source: neo_timetable.AcademicWeekNode
    target: neo_calendar.CalendarWeekNode
    
class CalendarWeekIsHolidayWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_HOLIDAY_WEEK'
    source: neo_calendar.CalendarWeekNode
    target: neo_timetable.HolidayWeekNode

class HolidayWeekIsCalendarWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_WEEK'
    source: neo_timetable.HolidayWeekNode
    target: neo_calendar.CalendarWeekNode

class CalendarDayIsAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_ACADEMIC_DAY'
    source: neo_calendar.CalendarDayNode
    target: neo_timetable.AcademicDayNode
    
class AcademicDayIsCalendarDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_DAY'
    source: neo_timetable.AcademicDayNode
    target: neo_calendar.CalendarDayNode
    
class CalendarDayIsHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_HOLIDAY_DAY'
    source: neo_calendar.CalendarDayNode
    target: neo_timetable.HolidayDayNode

class HolidayDayIsCalendarDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_DAY'
    source: neo_timetable.HolidayDayNode
    target: neo_calendar.CalendarDayNode
    
class CalendarDayIsOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_OFF_TIMETABLE_DAY'
    source: neo_calendar.CalendarDayNode
    target: neo_timetable.OffTimetableDayNode
    
class OffTimetableDayIsCalendarDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_DAY'
    source: neo_timetable.OffTimetableDayNode
    target: neo_calendar.CalendarDayNode
    
class CalendarDayIsStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_STAFF_DAY'
    source: neo_calendar.CalendarDayNode
    target: neo_timetable.StaffDayNode
    
class StaffDayIsCalendarDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS_CALENDAR_DAY'
    source: neo_timetable.StaffDayNode
    target: neo_calendar.CalendarDayNode