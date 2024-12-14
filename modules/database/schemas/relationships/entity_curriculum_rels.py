from typing import ClassVar, Union
import modules.database.schemas.curriculum_neo as neo_curriculum
import modules.database.schemas.entity_neo as neo_entity
from modules.database.tools.neontology.baserelationship import BaseRelationship

class SchoolHasCurriculumStructure(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_CURRICULUM_STRUCTURE'
    source: neo_entity.SchoolNode
    target: neo_curriculum.CurriculumStructureNode
    
class SchoolHasPastoralStructure(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'HAS_PASTORAL_STRUCTURE'
    source: neo_entity.SchoolNode
    target: neo_curriculum.PastoralStructureNode