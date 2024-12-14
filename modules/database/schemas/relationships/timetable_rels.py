import modules.database.schemas.timetable_neo as neo_timetable
from modules.database.tools.neontology.baserelationship import BaseRelationship
from typing import ClassVar

# Timetable hierarchy structure relationships
class AcademicTimetableHasAcademicYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TIMETABLE_HAS_ACADEMIC_YEAR'
    source: neo_timetable.SchoolTimetableNode
    target: neo_timetable.AcademicYearNode

class AcademicYearHasAcademicTerm(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_YEAR_HAS_ACADEMIC_TERM'
    source: neo_timetable.AcademicYearNode
    target: neo_timetable.AcademicTermNode

class AcademicYearHasAcademicTermBreak(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_YEAR_HAS_ACADEMIC_TERM_BREAK'
    source: neo_timetable.AcademicYearNode
    target: neo_timetable.AcademicTermBreakNode

class AcademicYearHasAcademicWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_YEAR_HAS_ACADEMIC_WEEK'
    source: neo_timetable.AcademicYearNode
    target: neo_timetable.AcademicWeekNode

class AcademicYearHasHolidayWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_YEAR_HAS_HOLIDAY_WEEK'
    source: neo_timetable.AcademicYearNode
    target: neo_timetable.HolidayWeekNode

class AcademicTermHasAcademicWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_HAS_ACADEMIC_WEEK'
    source: neo_timetable.AcademicTermNode
    target: neo_timetable.AcademicWeekNode

class AcademicTermBreakHasHolidayWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_BREAK_HAS_HOLIDAY_WEEK'
    source: neo_timetable.AcademicTermBreakNode
    target: neo_timetable.HolidayWeekNode

class AcademicTermBreakHasHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_BREAK_HAS_HOLIDAY_DAY'
    source: neo_timetable.AcademicTermBreakNode
    target: neo_timetable.HolidayDayNode

class AcademicTermHasAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_HAS_ACADEMIC_DAY'
    source: neo_timetable.AcademicTermNode
    target: neo_timetable.AcademicDayNode

class AcademicTermHasHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_HAS_HOLIDAY_DAY'
    source: neo_timetable.AcademicTermNode
    target: neo_timetable.HolidayDayNode

class AcademicTermHasOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_HAS_OFF_TIMETABLE_DAY'
    source: neo_timetable.AcademicTermNode
    target: neo_timetable.OffTimetableDayNode

class AcademicTermHasStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_HAS_STAFF_DAY'
    source: neo_timetable.AcademicTermNode
    target: neo_timetable.StaffDayNode

class AcademicWeekHasAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_HAS_ACADEMIC_DAY'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.AcademicDayNode

class AcademicWeekHasHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_HAS_HOLIDAY_DAY'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.HolidayDayNode

class AcademicWeekHasOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_HAS_OFF_TIMETABLE_DAY'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.OffTimetableDayNode

class AcademicWeekHasStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_HAS_STAFF_DAY'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.StaffDayNode

class HolidayWeekHasHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_WEEK_HAS_HOLIDAY_DAY'
    source: neo_timetable.HolidayWeekNode
    target: neo_timetable.HolidayDayNode

class AcademicDayHasAcademicPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_HAS_ACADEMIC_PERIOD'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.AcademicPeriodNode

class AcademicDayHasRegistrationPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_HAS_REGISTRATION_PERIOD'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.RegistrationPeriodNode

class AcademicDayHasBreakPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_HAS_BREAK_PERIOD'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.BreakPeriodNode

class AcademicDayHasOffTimetablePeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_HAS_OFF_TIMETABLE_PERIOD'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.OffTimetablePeriodNode

# Timetable sequence relationships
class AcademicYearFollowsAcademicYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_YEAR_FOLLOWS_ACADEMIC_YEAR'
    source: neo_timetable.AcademicYearNode
    target: neo_timetable.AcademicYearNode

class AcademicTermFollowsAcademicTermBreak(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_FOLLOWS_ACADEMIC_TERM_BREAK'
    source: neo_timetable.AcademicTermBreakNode  # Term break ends
    target: neo_timetable.AcademicTermNode      # New term starts

class AcademicTermBreakFollowsAcademicTerm(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_TERM_BREAK_FOLLOWS_ACADEMIC_TERM'
    source: neo_timetable.AcademicTermNode      # Term ends
    target: neo_timetable.AcademicTermBreakNode # Term break starts

class AcademicWeekFollowsAcademicWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_FOLLOWS_ACADEMIC_WEEK'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.AcademicWeekNode

class HolidayWeekFollowsHolidayWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_WEEK_FOLLOWS_HOLIDAY_WEEK'
    source: neo_timetable.HolidayWeekNode
    target: neo_timetable.HolidayWeekNode

class AcademicWeekFollowsHolidayWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_WEEK_FOLLOWS_HOLIDAY_WEEK'
    source: neo_timetable.HolidayWeekNode
    target: neo_timetable.AcademicWeekNode

class HolidayWeekFollowsAcademicWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_WEEK_FOLLOWS_ACADEMIC_WEEK'
    source: neo_timetable.AcademicWeekNode
    target: neo_timetable.HolidayWeekNode

class AcademicDayFollowsAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_FOLLOWS_ACADEMIC_DAY'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.AcademicDayNode

class AcademicDayFollowsHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_FOLLOWS_HOLIDAY_DAY'
    source: neo_timetable.HolidayDayNode
    target: neo_timetable.AcademicDayNode

class AcademicDayFollowsOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_FOLLOWS_OFF_TIMETABLE_DAY'
    source: neo_timetable.OffTimetableDayNode
    target: neo_timetable.AcademicDayNode

class AcademicDayFollowsStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_DAY_FOLLOWS_STAFF_DAY'
    source: neo_timetable.StaffDayNode
    target: neo_timetable.AcademicDayNode

class HolidayDayFollowsHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_DAY_FOLLOWS_HOLIDAY_DAY'
    source: neo_timetable.HolidayDayNode
    target: neo_timetable.HolidayDayNode

class HolidayDayFollowsAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_DAY_FOLLOWS_ACADEMIC_DAY'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.HolidayDayNode

class HolidayDayFollowsOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_DAY_FOLLOWS_OFF_TIMETABLE_DAY'
    source: neo_timetable.OffTimetableDayNode
    target: neo_timetable.HolidayDayNode

class HolidayDayFollowsStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HOLIDAY_DAY_FOLLOWS_STAFF_DAY'
    source: neo_timetable.StaffDayNode
    target: neo_timetable.HolidayDayNode

class OffTimetableDayFollowsOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_DAY_FOLLOWS_OFF_TIMETABLE_DAY'
    source: neo_timetable.OffTimetableDayNode
    target: neo_timetable.OffTimetableDayNode

class OffTimetableDayFollowsAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_DAY_FOLLOWS_ACADEMIC_DAY'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.OffTimetableDayNode

class OffTimetableDayFollowsHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_DAY_FOLLOWS_HOLIDAY_DAY'
    source: neo_timetable.HolidayDayNode
    target: neo_timetable.OffTimetableDayNode

class OffTimetableDayFollowsStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_DAY_FOLLOWS_STAFF_DAY'
    source: neo_timetable.StaffDayNode
    target: neo_timetable.OffTimetableDayNode

class StaffDayFollowsStaffDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'STAFF_DAY_FOLLOWS_STAFF_DAY'
    source: neo_timetable.StaffDayNode
    target: neo_timetable.StaffDayNode

class StaffDayFollowsAcademicDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'STAFF_DAY_FOLLOWS_ACADEMIC_DAY'
    source: neo_timetable.AcademicDayNode
    target: neo_timetable.StaffDayNode

class StaffDayFollowsHolidayDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'STAFF_DAY_FOLLOWS_HOLIDAY_DAY'
    source: neo_timetable.HolidayDayNode
    target: neo_timetable.StaffDayNode

class StaffDayFollowsOffTimetableDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'STAFF_DAY_FOLLOWS_OFF_TIMETABLE_DAY'
    source: neo_timetable.OffTimetableDayNode
    target: neo_timetable.StaffDayNode

class AcademicPeriodFollowsAcademicPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_PERIOD_FOLLOWS_ACADEMIC_PERIOD'
    source: neo_timetable.AcademicPeriodNode
    target: neo_timetable.AcademicPeriodNode

class AcademicPeriodFollowsBreakPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_PERIOD_FOLLOWS_BREAK_PERIOD'
    source: neo_timetable.BreakPeriodNode
    target: neo_timetable.AcademicPeriodNode

class AcademicPeriodFollowsRegistrationPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_PERIOD_FOLLOWS_REGISTRATION_PERIOD'
    source: neo_timetable.RegistrationPeriodNode
    target: neo_timetable.AcademicPeriodNode

class AcademicPeriodFollowsOffTimetablePeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'ACADEMIC_PERIOD_FOLLOWS_OFF_TIMETABLE_PERIOD'
    source: neo_timetable.OffTimetablePeriodNode
    target: neo_timetable.AcademicPeriodNode

class BreakPeriodFollowsAcademicPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BREAK_PERIOD_FOLLOWS_ACADEMIC_PERIOD'
    source: neo_timetable.AcademicPeriodNode
    target: neo_timetable.BreakPeriodNode

class RegistrationPeriodFollowsAcademicPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'REGISTRATION_PERIOD_FOLLOWS_ACADEMIC_PERIOD'
    source: neo_timetable.AcademicPeriodNode
    target: neo_timetable.RegistrationPeriodNode

class RegistrationPeriodFollowsOffTimetablePeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'REGISTRATION_PERIOD_FOLLOWS_OFF_TIMETABLE_PERIOD'
    source: neo_timetable.OffTimetablePeriodNode
    target: neo_timetable.RegistrationPeriodNode

class OffTimetablePeriodFollowsAcademicPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_PERIOD_FOLLOWS_ACADEMIC_PERIOD'
    source: neo_timetable.AcademicPeriodNode
    target: neo_timetable.OffTimetablePeriodNode

class OffTimetablePeriodFollowsRegistrationPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_PERIOD_FOLLOWS_REGISTRATION_PERIOD'
    source: neo_timetable.RegistrationPeriodNode
    target: neo_timetable.OffTimetablePeriodNode

class OffTimetablePeriodFollowsOffTimetablePeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_PERIOD_FOLLOWS_OFF_TIMETABLE_PERIOD'
    source: neo_timetable.OffTimetablePeriodNode
    target: neo_timetable.OffTimetablePeriodNode

class BreakPeriodFollowsBreakPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BREAK_PERIOD_FOLLOWS_BREAK_PERIOD'
    source: neo_timetable.BreakPeriodNode
    target: neo_timetable.BreakPeriodNode

class BreakPeriodFollowsRegistrationPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BREAK_PERIOD_FOLLOWS_REGISTRATION_PERIOD'
    source: neo_timetable.RegistrationPeriodNode
    target: neo_timetable.BreakPeriodNode

class BreakPeriodFollowsOffTimetablePeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BREAK_PERIOD_FOLLOWS_OFF_TIMETABLE_PERIOD'
    source: neo_timetable.OffTimetablePeriodNode
    target: neo_timetable.BreakPeriodNode

class RegistrationPeriodFollowsBreakPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'REGISTRATION_PERIOD_FOLLOWS_BREAK_PERIOD'
    source: neo_timetable.BreakPeriodNode
    target: neo_timetable.RegistrationPeriodNode

class OffTimetablePeriodFollowsBreakPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'OFF_TIMETABLE_PERIOD_FOLLOWS_BREAK_PERIOD'
    source: neo_timetable.BreakPeriodNode
    target: neo_timetable.OffTimetablePeriodNode

class RegistrationPeriodFollowsRegistrationPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'REGISTRATION_PERIOD_FOLLOWS_REGISTRATION_PERIOD'
    source: neo_timetable.RegistrationPeriodNode
    target: neo_timetable.RegistrationPeriodNode