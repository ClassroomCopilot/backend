from typing import ClassVar, Union
import modules.database.schemas.entity_neo as neo_entity
from modules.database.tools.neontology.baserelationship import BaseRelationship

class UserIsStandardUser(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS'
    source: neo_entity.UserNode
    target: Union[neo_entity.StandardUserNode, neo_entity.DeveloperNode]
    
class UserIsWorker(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'IS'
    source: neo_entity.UserNode
    target: Union[neo_entity.SchoolAdminNode, neo_entity.TeacherNode, neo_entity.StudentNode]

class EntityBelongsToSchool(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BELONGS_TO'
    source: Union[neo_entity.SchoolAdminNode, neo_entity.TeacherNode, neo_entity.StudentNode, neo_entity.SubjectClassNode, neo_entity.DepartmentNode, neo_entity.RoomNode]
    target: neo_entity.SchoolNode