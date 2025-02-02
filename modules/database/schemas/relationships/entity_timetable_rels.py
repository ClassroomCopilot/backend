from typing import ClassVar, Union
import modules.database.schemas.timetable_neo as neo_timetable
import modules.database.schemas.entity_neo as neo_entity
import modules.database.schemas.teacher_timetable_neo as neo_teacher_timetable
from modules.database.tools.neontology.baserelationship import BaseRelationship

class EntityHasTimetable(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_TIMETABLE'
    source: Union[neo_entity.UserNode, neo_entity.TeacherNode, neo_entity.StudentNode, neo_entity.SubjectClassNode]
    target: neo_teacher_timetable.UserTeacherTimetableNode
    

class SchoolHasTimetable(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_TIMETABLE'
    source: neo_entity.SchoolNode
    target: neo_timetable.SchoolTimetableNode