from neontology import BaseRelationship

class CalendarYearHasNextCalendarYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'CALENDAR_YEAR_HAS_NEXT_CALENDAR_YEAR'
    source: CalendarYearNode
    target: CalendarYearNode

class CalendarYearHasPreviousCalendarYear(BaseRelationship):
    __relationshiptype__: ClassVar[str] = 'CALENDAR_YEAR_HAS_PREVIOUS_CALENDAR_YEAR'
    source: CalendarYearNode
    target: CalendarYearNode