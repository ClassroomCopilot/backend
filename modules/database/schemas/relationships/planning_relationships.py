from typing import ClassVar, Union
from modules.database.tools.neontology.baserelationship import BaseRelationship
from modules.database.schemas.timetable_neo import AcademicPeriodNode, RegistrationPeriodNode
from modules.database.schemas.teacher_timetable_neo import TeacherTimetableNode, TimetableLessonNode, PlannedLessonNode, UserTimetableLessonNode
from modules.database.schemas.entity_neo import UserNode, TeacherNode, SubjectClassNode
from modules.database.schemas.curriculum_neo import YearGroupSyllabusNode

class TimetableLessonBelongsToPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'LESSON_BELONGS_TO_PERIOD'
    source: TimetableLessonNode
    target: Union[AcademicPeriodNode, RegistrationPeriodNode]

class TimetableLessonHasPlannedLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TIMETABLE_LESSON_HAS_PLANNED_LESSON'
    source: TimetableLessonNode
    target: PlannedLessonNode

class TeacherHasTimetable(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TEACHER_HAS_TIMETABLE'
    source: TeacherNode
    target: TeacherTimetableNode

class TimetableHasClass(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TIMETABLE_HAS_CLASS'
    source: TeacherTimetableNode
    target: SubjectClassNode
    
class ClassHasLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'CLASS_HAS_LESSON'
    source: SubjectClassNode
    target: TimetableLessonNode

class TimetableLessonFollowsTimetableLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TIMETABLE_LESSON_FOLLOWS_TIMETABLE_LESSON'
    source: Union[TimetableLessonNode, PlannedLessonNode, UserTimetableLessonNode]
    target: Union[TimetableLessonNode, PlannedLessonNode, UserTimetableLessonNode]
    

class PlannedLessonFollowsPlannedLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PLANNED_LESSON_FOLLOWS_PLANNED_LESSON'
    source: PlannedLessonNode
    target: PlannedLessonNode

class SubjectClassBelongsToYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'SUBJECT_CLASS_BELONGS_TO_YEAR_GROUP_SYLLABUS'
    source: SubjectClassNode
    target: YearGroupSyllabusNode