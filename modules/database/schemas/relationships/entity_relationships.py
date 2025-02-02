from typing import ClassVar, Union
import modules.database.schemas.entity_neo as neo_entity
import modules.database.schemas.curriculum_neo as neo_curriculum
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
    
class EntityBelongsToDepartment(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'BELONGS_TO'
    source: Union[neo_entity.SchoolAdminNode, neo_entity.TeacherNode, neo_entity.StudentNode, neo_entity.SubjectClassNode, neo_entity.DepartmentNode, neo_entity.RoomNode]
    target: neo_entity.DepartmentNode
    
class SchoolHasDepartmentStructure(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_DEPARTMENT_STRUCTURE'
    source: neo_entity.SchoolNode
    target: neo_entity.DepartmentStructureNode

class DepartmentStructureHasDepartment(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_DEPARTMENT'
    source: neo_entity.DepartmentStructureNode
    target: neo_entity.DepartmentNode

class DepartmentManagesKeyStageSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'MANAGES_KEY_STAGE_SYLLABUS'
    source: neo_entity.DepartmentNode
    target: neo_curriculum.KeyStageSyllabusNode

class DepartmentManagesSubject(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'MANAGES_SUBJECT'
    source: neo_entity.DepartmentNode
    target: neo_curriculum.SubjectNode

