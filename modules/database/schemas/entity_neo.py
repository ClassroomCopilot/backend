from typing import ClassVar, Optional
from modules.database.tools.neontology.basenode import BaseNode

# Neo4j Nodes and relationships using Neontology
# System entities layer
class UserNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'User'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    user_id: str
    user_type: str
    user_name: str
    user_email: str
    path: str
    worker_node_data: str

    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "user_id": self.user_id,
            "user_type": self.user_type,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "path": self.path,
            "worker_node_data": self.worker_node_data,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class StandardUserNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'StandardUser'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    user_name: str
    user_email: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class DeveloperNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Developer'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    user_name: str
    user_email: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

# School entities layer
class SchoolAdminNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'SchoolAdmin'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    user_name: str
    user_email: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class SchoolNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'School'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    school_uuid: str
    school_name: str
    school_website: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "school_uuid": self.school_uuid,
            "school_name": self.school_name,
            "school_website": self.school_website,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class DepartmentStructureNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'DepartmentStructure'
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
        
class DepartmentNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Department'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    department_name: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "department_name": self.department_name,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }
    
class TeacherNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Teacher'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    teacher_code: str
    teacher_name_formal: str
    teacher_email: str
    path: str
    worker_db_name: str
    user_db_name: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "teacher_code": self.teacher_code,
            "teacher_name_formal": self.teacher_name_formal,
            "teacher_email": self.teacher_email,
            "path": self.path,
            "worker_db_name": self.worker_db_name,
            "user_db_name": self.user_db_name,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class StudentNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Student'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    student_code: str
    student_name_formal: str
    student_email: str
    path: str
    worker_db_name: str
    user_db_name: str
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "student_code": self.student_code,
            "student_name_formal": self.student_name_formal,
            "student_email": self.student_email,
            "path": self.path,
            "worker_db_name": self.worker_db_name,
            "user_db_name": self.user_db_name,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class SubjectClassNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'SubjectClass'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    subject_class_code: str
    year_group: str
    subject: str
    subject_code: str
    path: str
    
    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "subject_class_code": self.subject_class_code,
            "year_group": self.year_group,
            "subject": self.subject,
            "subject_code": self.subject_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }

class RoomNode(BaseNode):
    __primarylabel__: ClassVar[str] = 'Room'
    __primaryproperty__: ClassVar[str] = 'unique_id'
    unique_id: str
    room_code: str
    path: str

    def to_dict(self):
        return {
            "__primarylabel__": self.__primarylabel__,
            "unique_id": self.unique_id,
            "room_code": self.room_code,
            "path": self.path,
            "created": self.created.isoformat() if self.created else None,
            "merged": self.merged.isoformat() if self.merged else None,
        }