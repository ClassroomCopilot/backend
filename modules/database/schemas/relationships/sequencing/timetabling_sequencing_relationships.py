from neontology import BaseRelationship   

class AcademicTermHasNextTerm(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TERM_HAS_NEXT_TERM'
    source: TermNode
    target: TermNode

class AcademicTermHasPreviousTerm(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'TERM_HAS_PREVIOUS_TERM'
    source: TermNode
    target: TermNode

class AcademicWeekHasNextWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'WEEK_HAS_NEXT_WEEK'
    source: WeekNode
    target: WeekNode

class AcademicWeekHasPreviousWeek(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'WEEK_HAS_PREVIOUS_WEEK'
    source: WeekNode
    target: WeekNode

class AcademicDayHasNextDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'DAY_HAS_NEXT_DAY'
    source: DayNode
    target: DayNode

class AcademicDayHasPreviousDay(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'DAY_HAS_PREVIOUS_DAY'
    source: DayNode
    target: DayNode

class AcademicPeriodHasNextPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PERIOD_HAS_NEXT_PERIOD'
    source: PeriodNode
    target: PeriodNode

class AcademicPeriodHasPreviousPeriod(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'PERIOD_HAS_PREVIOUS_PERIOD'
    source: PeriodNode
    target: PeriodNode