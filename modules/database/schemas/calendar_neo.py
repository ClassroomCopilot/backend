from modules.database.tools.neontology.basenode import BaseNode
import datetime
from typing import ClassVar

# Neo4j Nodes and relationships using Neontology
# Calendar layer
class CalendarNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Calendar'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    name: str
    start_date: datetime.date
    end_date: datetime.date
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "name": self.name,
            "path": self.path,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class CalendarYearNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CalendarYear'
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


class CalendarMonthNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CalendarMonth'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    year: str
    month: str
    month_name: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "year": self.year,
            "month": self.month,
            "month_name": self.month_name,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }


class CalendarWeekNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CalendarWeek'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    start_date: datetime.date
    week_number: str
    iso_week: str  # ISO 8601 week
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "week_number": self.week_number,
            "iso_week": self.iso_week,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class CalendarDayNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CalendarDay'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    date: datetime.date
    day_of_week: str
    iso_day: str  # ISO 8601 day
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "date": self.date.isoformat() if self.date else None,
            "day_of_week": self.day_of_week,
            "iso_day": self.iso_day,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class CalendarTimeChunkNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CalendarTimeChunk'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    start_time: datetime.time
    end_time: datetime.time
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
