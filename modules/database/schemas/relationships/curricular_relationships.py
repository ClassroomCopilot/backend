import modules.database.schemas.curriculum_neo as neo_curriculum
from modules.database.tools.neontology.baserelationship import BaseRelationship
from typing import ClassVar

# Structure layer relationships
class CurriculumStructureIncludesKeyStage(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'CURRICULUM_STRUCTURE_INCLUDES_KEY_STAGE'
    source: neo_curriculum.CurriculumStructureNode
    target: neo_curriculum.KeyStageNode
    
class PastoralStructureIncludesYearGroup(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PASTORAL_STRUCTURE_INCLUDES_YEAR_GROUP'
    source: neo_curriculum.PastoralStructureNode
    target: neo_curriculum.YearGroupNode

## Curriculum layer relationships
class SubjectForKeyStage(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'SUBJECT_FOR_KEY_STAGE'
    source: neo_curriculum.SubjectNode
    target: neo_curriculum.KeyStageNode
    
class SubjectHasYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'SUBJECT_HAS_YEAR_GROUP_SYLLABUS'
    source: neo_curriculum.SubjectNode
    target: neo_curriculum.YearGroupSyllabusNode
    
class SubjectHasKeyStageSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'SUBJECT_HAS_KEY_STAGE_SYLLABUS'
    source: neo_curriculum.SubjectNode
    target: neo_curriculum.KeyStageSyllabusNode

class TopicPartOfYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_SYLLABUS_INCLUDES_TOPIC'
    source: neo_curriculum.YearGroupSyllabusNode
    target: neo_curriculum.TopicNode
    
class KeyStageSyllabusIncludesTopic(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_SYLLABUS_INCLUDES_TOPIC'
    source: neo_curriculum.KeyStageSyllabusNode
    target: neo_curriculum.TopicNode

class YearGroupHasYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_GROUP_HAS_YEAR_GROUP_SYLLABUS'
    source: neo_curriculum.YearGroupNode
    target: neo_curriculum.YearGroupSyllabusNode

class KeyStageSyllabusIncludesYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_SYLLABUS_INCLUDES_YEAR_GROUP_SYLLABUS'
    source: neo_curriculum.KeyStageSyllabusNode
    target: neo_curriculum.YearGroupSyllabusNode

class KeyStageIncludesKeyStageSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_INCLUDES_KEY_STAGE_SYLLABUS'
    source: neo_curriculum.KeyStageNode
    target: neo_curriculum.KeyStageSyllabusNode

class KeyStageIncludesTopic(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_INCLUDES_TOPIC'
    source: neo_curriculum.KeyStageNode
    target: neo_curriculum.TopicNode

class SubjectIncludesTopic(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'SUBJECT_INCLUDES_TOPIC'
    source: neo_curriculum.SubjectNode
    target: neo_curriculum.TopicNode

class TopicIncludesTopicLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TOPIC_INCLUDES_LESSON'
    source: neo_curriculum.TopicNode
    target: neo_curriculum.TopicLessonNode

class TopicIncludesLearningStatement(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TOPIC_INCLUDES_LEARNING_STATEMENT'
    source: neo_curriculum.TopicNode
    target: neo_curriculum.LearningStatementNode

class LessonIncludesLearningStatement(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'LESSON_INCLUDES_LEARNING_STATEMENT'
    source: neo_curriculum.TopicLessonNode
    target: neo_curriculum.LearningStatementNode

# Science-specific curriculum layer relationships
class TopicLessonIncludesScienceLab(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'LESSON_INCLUDES_SCIENCE_LAB'
    source: neo_curriculum.TopicLessonNode
    target: neo_curriculum.ScienceLabNode
    

class KeyStageFollowsKeyStage(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_FOLLOWS_KEY_STAGE'
    source: neo_curriculum.KeyStageNode
    target: neo_curriculum.KeyStageNode

class YearGroupFollowsYearGroup(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_GROUP_FOLLOWS_YEAR_GROUP'
    source: neo_curriculum.YearGroupNode
    target: neo_curriculum.YearGroupNode

class KeyStageSyllabusFollowsKeyStageSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'KEY_STAGE_SYLLABUS_FOLLOWS_KEY_STAGE_SYLLABUS'
    source: neo_curriculum.KeyStageSyllabusNode
    target: neo_curriculum.KeyStageSyllabusNode

class YearGroupSyllabusFollowsYearGroupSyllabus(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_GROUP_SYLLABUS_FOLLOWS_YEAR_GROUP_SYLLABUS'
    source: neo_curriculum.YearGroupSyllabusNode
    target: neo_curriculum.YearGroupSyllabusNode

class TopicLessonFollowsTopicLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'LESSON_FOLLOWS_LESSON'
    source: neo_curriculum.TopicLessonNode
    target: neo_curriculum.TopicLessonNode
    
class YearGroupSyllabusIncludesTopic(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'YEAR_GROUP_SYLLABUS_INCLUDES_TOPIC'
    source: neo_curriculum.YearGroupSyllabusNode
    target: neo_curriculum.TopicNode
