from neontology import BaseRelationship

class PlannedLessonHasNextPlannedLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PLANNED_LESSON_HAS_NEXT_PLANNED_LESSON'
    source: PlannedLessonNode
    target: PlannedLessonNode

class PlannedLessonHasPreviousPlannedLesson(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PLANNED_LESSON_HAS_PREVIOUS_PLANNED_LESSON'
    source: PlannedLessonNode
    target: PlannedLessonNode