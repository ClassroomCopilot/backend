from modules.database.tools.neontology.basenode import BaseNode
import datetime
from typing import ClassVar

# Timetable layer
class SchoolTimetableNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'SchoolTimetable'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    start_date: datetime.date
    end_date: datetime.date
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class AcademicYearNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicYear'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    year: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "year": self.year,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class AcademicTermNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicTerm'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    term_name: str
    term_number: str
    start_date: datetime.date
    end_date: datetime.date
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "term_name": self.term_name,
            "term_number": self.term_number,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class AcademicTermBreakNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicTermBreak'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    term_break_name: str
    start_date: datetime.date
    end_date: datetime.date
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "term_break_name": self.term_break_name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class AcademicWeekNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicWeek'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    academic_week_number: str
    start_date: datetime.date
    week_type: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "academic_week_number": self.academic_week_number,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "week_type": self.week_type,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class HolidayWeekNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'HolidayWeek'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    start_date: datetime.date
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class AcademicDayNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicDay'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    academic_day: str
    date: datetime.date
    day_of_week: str
    day_type: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "academic_day": self.academic_day,
            "date": self.date.isoformat() if self.date else None,
            "day_of_week": self.day_of_week,
            "day_type": self.day_type,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    


class OffTimetableDayNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'OffTimetableDay'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    date: datetime.date
    day_of_week: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "date": self.date.isoformat() if self.date else None,
            "day_of_week": self.day_of_week,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class StaffDayNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'StaffDay'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    date: datetime.date
    day_of_week: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "date": self.date.isoformat() if self.date else None,
            "day_of_week": self.day_of_week,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class HolidayDayNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'HolidayDay'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    date: datetime.date
    day_of_week: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "date": self.date.isoformat() if self.date else None,
            "day_of_week": self.day_of_week,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
        
class AcademicPeriodNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'AcademicPeriod'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    name: str
    date: datetime.date
    start_time: datetime.datetime
    end_time: datetime.datetime
    period_code: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "period_code": self.period_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    

class RegistrationPeriodNode(BaseNode):

    __primarylabel__: ClassVar[str] = 'RegistrationPeriod'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    name: str
    date: datetime.date
    start_time: datetime.datetime
    end_time: datetime.datetime
    period_code: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "period_code": self.period_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class BreakPeriodNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'BreakPeriod'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    name: str
    date: datetime.date
    start_time: datetime.datetime
    end_time: datetime.datetime
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class OffTimetablePeriodNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'OffTimetablePeriod'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    name: str
    date: datetime.date
    start_time: datetime.datetime
    end_time: datetime.datetime
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
