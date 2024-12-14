from typing import ClassVar, Union
import modules.database.schemas.calendar_neo as neo_calendar
import modules.database.schemas.entity_neo as neo_entity
from modules.database.tools.neontology.baserelationship import BaseRelationship

class EntityHasCalendar(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_CALENDAR'
    source: Union[neo_entity.UserNode, neo_entity.StandardUserNode, neo_entity.DeveloperNode, neo_entity.SchoolNode, neo_entity.DepartmentNode, neo_entity.TeacherNode, neo_entity.StudentNode, neo_entity.SubjectClassNode, neo_entity.RoomNode]
    target: neo_calendar.CalendarNode