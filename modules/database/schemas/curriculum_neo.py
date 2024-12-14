from modules.database.tools.neontology.basenode import BaseNode
from typing import ClassVar, Optional

# Pastoral layer
class PastoralStructureNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'PastoralStructure'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class YearGroupNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'YearGroup'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    year_group: Optional[str] = None
    year_group_name: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "year_group": self.year_group,
            "year_group_name": self.year_group_name,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

# Curriculum layer

class CurriculumStructureNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'CurriculumStructure'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class KeyStageNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'KeyStage'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    key_stage_name: Optional[str] = None
    key_stage: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "key_stage_name": self.key_stage_name,
            "key_stage": self.key_stage,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }


class KeyStageSyllabusNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'KeyStageSyllabus'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    ks_syllabus_id: str
    ks_syllabus_name: Optional[str] = None
    ks_syllabus_key_stage: Optional[str] = None
    ks_syllabus_subject: Optional[str] = None
    ks_syllabus_subject_code: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "ks_syllabus_id": self.ks_syllabus_id,
            "ks_syllabus_name": self.ks_syllabus_name,
            "ks_syllabus_key_stage": self.ks_syllabus_key_stage,
            "ks_syllabus_subject": self.ks_syllabus_subject,
            "ks_syllabus_subject_code": self.ks_syllabus_subject_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class YearGroupSyllabusNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'YearGroupSyllabus'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    yr_syllabus_id: str
    yr_syllabus_name: Optional[str] = None
    yr_syllabus_year_group: Optional[str] = None
    yr_syllabus_subject: Optional[str] = None
    yr_syllabus_subject_code: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "yr_syllabus_id": self.yr_syllabus_id,
            "yr_syllabus_name": self.yr_syllabus_name,
            "yr_syllabus_year_group": self.yr_syllabus_year_group,
            "yr_syllabus_subject": self.yr_syllabus_subject,
            "yr_syllabus_subject_code": self.yr_syllabus_subject_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }


class SubjectNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Subject'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "subject_code": self.subject_code,
            "subject_name": self.subject_name,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
        

class TopicNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Topic'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    total_number_of_lessons_for_topic: Optional[str] = None
    topic_type: Optional[str] = None
    topic_assessment_type: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "topic_id": self.topic_id,
            "topic_title": self.topic_title,
            "total_number_of_lessons_for_topic": self.total_number_of_lessons_for_topic,
            "topic_type": self.topic_type,
            "topic_assessment_type": self.topic_assessment_type,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    



class TopicLessonNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'TopicLesson'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    topic_lesson_id: str
    topic_lesson_title: Optional[str] = None
    topic_lesson_type: Optional[str] = None
    topic_lesson_length: Optional[str] = None
    topic_lesson_suggested_activities: Optional[str] = None
    topic_lesson_skills_learned: Optional[str] = None
    topic_lesson_weblinks: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "topic_lesson_id": self.topic_lesson_id,
            "topic_lesson_title": self.topic_lesson_title,
            "topic_lesson_type": self.topic_lesson_type,
            "topic_lesson_length": self.topic_lesson_length,
            "topic_lesson_suggested_activities": self.topic_lesson_suggested_activities,
            "topic_lesson_skills_learned": self.topic_lesson_skills_learned,
            "topic_lesson_weblinks": self.topic_lesson_weblinks,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class LearningStatementNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'LearningStatement'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    lesson_learning_statement_id: str
    lesson_learning_statement: Optional[str] = None
    lesson_learning_statement_type: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "lesson_learning_statement_id": self.lesson_learning_statement_id,
            "lesson_learning_statement": self.lesson_learning_statement,
            "lesson_learning_statement_type": self.lesson_learning_statement_type,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class ScienceLabNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'ScienceLab'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    science_lab_id: str
    science_lab_title: Optional[str] = None
    science_lab_summary: Optional[str] = None
    science_lab_requirements: Optional[str] = None
    science_lab_procedure: Optional[str] = None
    science_lab_safety: Optional[str] = None
    science_lab_weblinks: Optional[str] = None
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "science_lab_id": self.science_lab_id,
            "science_lab_title": self.science_lab_title,
            "science_lab_summary": self.science_lab_summary,
            "science_lab_requirements": self.science_lab_requirements,
            "science_lab_procedure": self.science_lab_procedure,
            "science_lab_safety": self.science_lab_safety,
            "science_lab_weblinks": self.science_lab_weblinks,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
