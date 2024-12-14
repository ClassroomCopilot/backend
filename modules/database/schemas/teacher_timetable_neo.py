from modules.database.tools.neontology.basenode import BaseNode
import datetime
from typing import ClassVar, Optional, List

# Timetable layer
class TeacherTimetableNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'TeacherTimetable'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class TimetableLessonNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'TimetableLesson'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    subject_class: str
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    period_code: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "subject_class": self.subject_class,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "period_code": self.period_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class PlannedLessonNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'PlannedLesson'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    period_code: str
    subject_class: str
    year_group: str
    subject: str
    teacher_code: str
    planning_status: str
    topic_code: Optional[str] = None
    topic_name: Optional[str] = None
    lesson_code: Optional[str] = None
    lesson_name: Optional[str] = None
    learning_statement_codes: Optional[List[str]] = None
    learning_statements: Optional[List[str]] = None
    learning_resource_codes: Optional[List[str]] = None
    learning_resources: Optional[List[str]] = None
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "period_code": self.period_code,
            "subject_class": self.subject_class,
            "year_group": self.year_group,
            "subject": self.subject,
            "teacher_code": self.teacher_code,
            "planning_status": self.planning_status,
            "topic_code": self.topic_code,
            "topic_name": self.topic_name,
            "lesson_code": self.lesson_code,
            "lesson_name": self.lesson_name,
            "learning_statement_codes": self.learning_statement_codes,
            "learning_statements": self.learning_statements,
            "learning_resource_codes": self.learning_resource_codes,
            "learning_resources": self.learning_resources,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
