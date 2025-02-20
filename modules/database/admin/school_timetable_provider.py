import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

import modules.database.init.init_calendar as init_calendar
import modules.database.schemas.timetable_neo as timetable_neo
import modules.database.schemas.relationships.timetable_rels as tt_rels
import modules.database.schemas.relationships.entity_timetable_rels as entity_tt_rels
import modules.database.schemas.relationships.calendar_timetable_rels as cal_tt_rels
import modules.database.tools.neontology_tools as neon
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from datetime import timedelta, datetime
import pandas as pd

def create_school_timetable_from_dataframes(dataframes, db_name, school_node=None):
    logger.info(f"Creating school timetable for {db_name}")
    if dataframes is None:
        raise ValueError("Data is required to create the calendar and timetable.")

    logger.info("Initialising neo4j connection...")
    neon.init_neontology_connection()

    # Initialize the filesystem handler
    fs_handler = ClassroomCopilotFilesystem(db_name, init_run_type="school")

    school_df = dataframes['school']
    if school_node is None:
        logger.info("School node is None, using school data from dataframe")
        school_unique_id = school_df[school_df['Identifier'] == 'SchoolID']['Data'].iloc[0]
    else:
        logger.info(f"School node is not None, using school data from school node: {school_node}")
        school_unique_id = school_node.unique_id

    terms_df = dataframes['terms']
    weeks_df = dataframes['weeks']
    days_df = dataframes['days']
    periods_df = dataframes['periods']

    school_df_year_start = school_df[school_df['Identifier'] == 'AcademicYearStart']['Data'].iloc[0]
    school_df_year_end = school_df[school_df['Identifier'] == 'AcademicYearEnd']['Data'].iloc[0]
    if isinstance(school_df_year_start, str):
        school_year_start_date = datetime.strptime(school_df_year_start, '%Y-%m-%d')
    else:
        school_year_start_date = school_df_year_start
    if isinstance(school_df_year_end, str):
        school_year_end_date = datetime.strptime(school_df_year_end, '%Y-%m-%d')
    else:
        school_year_end_date = school_df_year_end

    # Create a dictionary to store the timetable nodes
    timetable_nodes = {
        'timetable_node': None,
        'academic_year_nodes': [],
        'academic_term_nodes': [],
        'academic_week_nodes': [],
        'academic_day_nodes': [],
        'academic_period_nodes': []
    }

    if school_node:
        # Create the root timetable directory
        _, timetable_path = fs_handler.create_school_timetable_directory(school_node.path)
    else:
        # Create the root timetable directory
        _, timetable_path = fs_handler.create_school_timetable_directory()

    # Create AcademicTimetable Node
    school_timetable_unique_id = f"SchoolTimetable_{school_unique_id}_{school_year_start_date.year}_{school_year_end_date.year}"
    school_timetable_node = timetable_neo.SchoolTimetableNode(
        unique_id=school_timetable_unique_id,
        start_date=school_year_start_date,
        end_date=school_year_end_date,
        path=timetable_path
    )
    neon.create_or_merge_neontology_node(school_timetable_node, database=db_name, operation='merge')
    # Create the tldraw file for the node
    fs_handler.create_default_tldraw_file(school_timetable_node.path, school_timetable_node.to_dict())
    timetable_nodes['timetable_node'] = school_timetable_node

    if school_node:
        logger.info(f"Creating calendar for {school_unique_id} from Neo4j SchoolNode: {school_node.unique_id}")
        calendar_nodes = init_calendar.create_calendar(db_name, school_year_start_date, school_year_end_date, attach_to_calendar_node=True, entity_node=school_node)
        # Link the school node to the timetable node
        neon.create_or_merge_neontology_relationship(
            entity_tt_rels.SchoolHasTimetable(source=school_node, target=school_timetable_node),
            database=db_name, operation='merge'
        )
        timetable_nodes['calendar_nodes'] = calendar_nodes
    else:
        logger.info(f"Creating calendar for {school_unique_id} from dataframe SchoolID: {school_unique_id}")
        calendar_nodes = init_calendar.create_calendar(db_name, school_year_start_date, school_year_end_date, attach_to_calendar_node=False, entity_node=None)

    # Create AcademicYear nodes for each year within the range
    for year in range(school_year_start_date.year, school_year_end_date.year + 1):
        _, timetable_year_path = fs_handler.create_school_timetable_year_directory(timetable_path, year)
        year_str = str(year)
        academic_year_unique_id = f"AcademicYear_{school_timetable_unique_id}_{year}"
        academic_year_node = timetable_neo.AcademicYearNode(
            unique_id=academic_year_unique_id,
            year=year_str,
            path=timetable_year_path
        )
        neon.create_or_merge_neontology_node(academic_year_node, database=db_name, operation='merge')
        # Create the tldraw file for the node
        fs_handler.create_default_tldraw_file(academic_year_node.path, academic_year_node.to_dict())
        timetable_nodes['academic_year_nodes'].append(academic_year_node)
        logger.info(f'Created academic year node: {academic_year_node.unique_id}')
        neon.create_or_merge_neontology_relationship(
            tt_rels.AcademicTimetableHasAcademicYear(source=school_timetable_node, target=academic_year_node),
            database=db_name, operation='merge'
        )
        logger.info(f"Created school timetable relationship from {school_timetable_node.unique_id} to {academic_year_node.unique_id}")

        # Link the academic year with the corresponding calendar year node
        for year_node in calendar_nodes['calendar_year_nodes']:
            if year_node.year == year:
                neon.create_or_merge_neontology_relationship(
                    cal_tt_rels.AcademicYearIsCalendarYear(source=academic_year_node, target=year_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created school timetable relationship from {academic_year_node.unique_id} to {year_node.unique_id}")
                break

    # Create Term and TermBreak nodes linked to AcademicYear
    term_number = 1
    academic_term_number = 1
    for _, term_row in terms_df.iterrows():
        term_node_class = timetable_neo.AcademicTermNode if term_row['TermType'] == 'Term' else timetable_neo.AcademicTermBreakNode
        term_name = term_row['TermName']
        term_name_no_spaces = term_name.replace(' ', '')
        term_start_date = term_row['StartDate']
        if isinstance(term_start_date, pd.Timestamp):
            term_start_date = term_start_date.strftime('%Y-%m-%d')

        term_end_date = term_row['EndDate']
        if isinstance(term_end_date, pd.Timestamp):
            term_end_date = term_end_date.strftime('%Y-%m-%d')

        if term_row['TermType'] == 'Term':
            _, timetable_term_path = fs_handler.create_school_timetable_academic_term_directory(
                timetable_path=timetable_path,
                term_name=term_name,
                term_number=academic_term_number
            )
            term_node_unique_id = f"AcademicTerm_{school_timetable_unique_id}_{academic_term_number}_{term_name_no_spaces}"
            academic_term_number_str = str(academic_term_number)
            term_node = term_node_class(
                unique_id=term_node_unique_id,
                term_name=term_name,
                term_number=academic_term_number_str,
                start_date=datetime.strptime(term_start_date, '%Y-%m-%d'),
                end_date=datetime.strptime(term_end_date, '%Y-%m-%d'),
                path=timetable_term_path
            )
            academic_term_number += 1
        else:
            term_break_node_unique_id = f"AcademicTermBreak_{school_timetable_unique_id}_{term_name_no_spaces}"
            term_node = term_node_class(
                unique_id=term_break_node_unique_id,
                term_break_name=term_name,
                start_date=datetime.strptime(term_start_date, '%Y-%m-%d'),
                end_date=datetime.strptime(term_end_date, '%Y-%m-%d')
            )
        neon.create_or_merge_neontology_node(term_node, database=db_name, operation='merge')
        if isinstance(term_node, timetable_neo.AcademicTermNode):
            # Create the tldraw file for the node
            fs_handler.create_default_tldraw_file(term_node.path, term_node.to_dict())
        logger.info(f'Created academic term break node: {term_node.unique_id}')
        timetable_nodes['academic_term_nodes'].append(term_node)
        term_number += 1 # We don't use this but we could

        # Link term node to the correct academic year
        term_years = set()
        term_years.update([term_node.start_date.year, term_node.end_date.year])

        for academic_year_node in timetable_nodes['academic_year_nodes']:
            if int(academic_year_node.year) in term_years:
                relationship_class = tt_rels.AcademicYearHasAcademicTerm if term_row['TermType'] == 'Term' else tt_rels.AcademicYearHasAcademicTermBreak
                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=academic_year_node, target=term_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created school timetable relationship from {academic_year_node.unique_id} to {term_node.unique_id}")

    # Create Week nodes
    academic_week_number = 1
    for _, week_row in weeks_df.iterrows():
        week_node_class = timetable_neo.HolidayWeekNode if week_row['WeekType'] == 'Holiday' else timetable_neo.AcademicWeekNode
        week_start_date = week_row['WeekStart']
        if isinstance(week_start_date, pd.Timestamp):
            week_start_date = week_start_date.strftime('%Y-%m-%d')

        if week_row['WeekType'] == 'Holiday':
            week_node_unique_id = f"{week_row['WeekType']}Week_{school_timetable_unique_id}_Week_{week_row['WeekNumber']}"
            week_node = week_node_class(
                unique_id=week_node_unique_id,
                start_date=datetime.strptime(week_start_date, '%Y-%m-%d')
            )
        else:
            _, timetable_week_path = fs_handler.create_school_timetable_academic_week_directory(
                timetable_path=timetable_path,
                week_number=academic_week_number
            )
            week_node_unique_id = f"AcademicWeek_{school_timetable_unique_id}_Week_{week_row['WeekNumber']}"
            academic_week_number_str = str(academic_week_number)
            week_type = week_row['WeekType']
            week_node = week_node_class(
                unique_id=week_node_unique_id,
                academic_week_number=academic_week_number_str,
                start_date=datetime.strptime(week_start_date, '%Y-%m-%d'),
                week_type=week_type,
                path=timetable_week_path
            )
            academic_week_number += 1
        neon.create_or_merge_neontology_node(week_node, database=db_name, operation='merge')
        timetable_nodes['academic_week_nodes'].append(week_node)
        logger.info(f"Created week node: {week_node.unique_id}")
        if isinstance(week_node, timetable_neo.AcademicWeekNode):
            # Create the tldraw file for the node
            fs_handler.create_default_tldraw_file(week_node.path, week_node.to_dict())
        for calendar_node in calendar_nodes['calendar_week_nodes']:
            if calendar_node.start_date == week_node.start_date:
                if isinstance(week_node, timetable_neo.AcademicWeekNode):
                    neon.create_or_merge_neontology_relationship(
                        cal_tt_rels.AcademicWeekIsCalendarWeek(source=week_node, target=calendar_node),
                        database=db_name, operation='merge'
                    )
                    logger.info(f"Created school timetable relationship from {calendar_node.unique_id} to {week_node.unique_id}")
                elif isinstance(week_node, timetable_neo.HolidayWeekNode):
                    neon.create_or_merge_neontology_relationship(
                        cal_tt_rels.HolidayWeekIsCalendarWeek(source=week_node, target=calendar_node),
                        database=db_name, operation='merge'
                    )
                    logger.info(f"Created school timetable relationship from {calendar_node.unique_id} to {week_node.unique_id}")
                break

        # Link week node to the correct academic term
        for term_node in timetable_nodes['academic_term_nodes']:
            if term_node.start_date <= week_node.start_date <= term_node.end_date:
                relationship_class = tt_rels.AcademicTermHasAcademicWeek if week_row['WeekType'] != 'Holiday' else tt_rels.AcademicTermBreakHasHolidayWeek
                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=term_node, target=week_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created school timetable relationship from {term_node.unique_id} to {week_node.unique_id}")
                break

        # Link week node to the correct academic year
        for academic_year_node in timetable_nodes['academic_year_nodes']:
            if int(academic_year_node.year) == week_node.start_date.year:
                relationship_class = tt_rels.AcademicYearHasAcademicWeek if week_row['WeekType'] != 'Holiday' else tt_rels.AcademicYearHasHolidayWeek
                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=academic_year_node, target=week_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created school timetable relationship from {academic_year_node.unique_id} to {week_node.unique_id}")
                break

    # Create Day nodes
    day_number = 1
    academic_day_number = 1
    for _, day_row in days_df.iterrows():        
        date_str = day_row['Date']
        if isinstance(date_str, pd.Timestamp):
            date_str = date_str.strftime('%Y-%m-%d')

        day_node_class = {
            'Academic': timetable_neo.AcademicDayNode,
            'Holiday': timetable_neo.HolidayDayNode,
            'OffTimetable': timetable_neo.OffTimetableDayNode,
            'StaffDay': timetable_neo.StaffDayNode
        }[day_row['DayType']]

        # Format the unique ID as {day_node_class.__name__}Day
        day_node_data = {
            'unique_id': f"{day_node_class.__name__}Day_{school_timetable_unique_id}_{day_number}",
            'date': datetime.strptime(date_str, '%Y-%m-%d'),
            'day_of_week': datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
        }

        if day_row['DayType'] == 'Academic':  
            day_node_data['academic_day'] = str(academic_day_number)
            day_node_data['day_type'] = day_row['WeekType']
            _, timetable_day_path = fs_handler.create_school_timetable_academic_day_directory(
                timetable_path=timetable_path,
                academic_day=academic_day_number
            )
            day_node_data['path'] = timetable_day_path

        day_node = day_node_class(**day_node_data)

        for calendar_node in calendar_nodes['calendar_day_nodes']:
            if calendar_node.date == day_node.date:
                neon.create_or_merge_neontology_node(day_node, database=db_name, operation='merge')
                timetable_nodes['academic_day_nodes'].append(day_node)
                logger.info(f"Created day node: {day_node.unique_id}")

                if isinstance(day_node, timetable_neo.AcademicDayNode):
                    fs_handler.create_default_tldraw_file(day_node.path, day_node.to_dict())
                    relationship_class = cal_tt_rels.AcademicDayIsCalendarDay
                elif isinstance(day_node, timetable_neo.HolidayDayNode):
                    relationship_class = cal_tt_rels.HolidayDayIsCalendarDay
                elif isinstance(day_node, timetable_neo.OffTimetableDayNode):
                    relationship_class = cal_tt_rels.OffTimetableDayIsCalendarDay
                elif isinstance(day_node, timetable_neo.StaffDayNode):
                    relationship_class = cal_tt_rels.StaffDayIsCalendarDay

                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=day_node, target=calendar_node),
                    database=db_name, operation='merge'
                )
                logger.info(f'Created relationship from {calendar_node.unique_id} to {day_node.unique_id}')
                break

        # Link day node to the correct academic week
        for academic_week_node in timetable_nodes['academic_week_nodes']:
            if academic_week_node.start_date <= day_node.date <= (academic_week_node.start_date + timedelta(days=6)):
                if day_row['DayType'] == 'Academic':
                    relationship_class = tt_rels.AcademicWeekHasAcademicDay
                elif day_row['DayType'] == 'Holiday':
                    if hasattr(academic_week_node, 'week_type') and academic_week_node.week_type in ['A', 'B']:
                        relationship_class = tt_rels.AcademicWeekHasHolidayDay
                    else:
                        relationship_class = tt_rels.HolidayWeekHasHolidayDay
                elif day_row['DayType'] == 'OffTimetable':
                    relationship_class = tt_rels.AcademicWeekHasOffTimetableDay
                elif day_row['DayType'] == 'Staff':
                    relationship_class = tt_rels.AcademicWeekHasStaffDay
                else:
                    continue  # Skip linking for other day types
                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=academic_week_node, target=day_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created relationship from {academic_week_node.unique_id} to {day_node.unique_id}")
                break

        # Link day node to the correct academic term
        for term_node in timetable_nodes['academic_term_nodes']:
            if term_node.start_date <= day_node.date <= term_node.end_date:
                if day_row['DayType'] == 'Academic':
                    relationship_class = tt_rels.AcademicTermHasAcademicDay
                elif day_row['DayType'] == 'Holiday':
                    if isinstance(term_node, timetable_neo.AcademicTermNode):
                        relationship_class = tt_rels.AcademicTermHasHolidayDay
                    else:
                        relationship_class = tt_rels.AcademicTermBreakHasHolidayDay
                elif day_row['DayType'] == 'OffTimetable':
                    relationship_class = tt_rels.AcademicTermHasOffTimetableDay
                elif day_row['DayType'] == 'Staff':
                    relationship_class = tt_rels.AcademicTermHasStaffDay
                else:
                    continue  # Skip linking for other day types
                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=term_node, target=day_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created relationship from {term_node.unique_id} to {day_node.unique_id}")
                break

        # Create Period nodes for each academic day
        if day_row['DayType'] == 'Academic':
            logger.info(f"Creating periods for {day_node.unique_id}")
            period_of_day = 1
            academic_or_registration_period_of_day = 1
            for _, period_row in periods_df.iterrows():
                period_node_class = {
                    'Academic': timetable_neo.AcademicPeriodNode,
                    'Registration': timetable_neo.RegistrationPeriodNode,
                    'Break': timetable_neo.BreakPeriodNode,
                    'OffTimetable': timetable_neo.OffTimetablePeriodNode
                }[period_row['PeriodType']]

                logger.info(f"Creating period node for {period_node_class.__name__} Period: {period_of_day}")
                period_node_unique_id = f"{period_node_class.__name__}_{school_timetable_unique_id}_Day_{academic_day_number}_Period_{period_of_day}"
                logger.debug(f"Period node unique id: {period_node_unique_id}")
                period_node_data = {
                    'unique_id': period_node_unique_id,
                    'name': period_row['PeriodName'],
                    'date': day_node.date,
                    'start_time': datetime.combine(day_node.date, period_row['StartTime']),
                    'end_time': datetime.combine(day_node.date, period_row['EndTime'])
                }
                logger.debug(f"Period node data: {period_node_data}")
                if period_row['PeriodType'] in ['Academic', 'Registration']:
                    _, timetable_period_path = fs_handler.create_school_timetable_period_directory(
                        timetable_path=timetable_path,
                        academic_day=academic_day_number,
                        period_dir=f"{academic_or_registration_period_of_day}_{period_row['PeriodName'].replace(' ', '_')}"
                    )
                    week_type = day_row['WeekType']
                    day_name_short = day_node.day_of_week[:3]
                    period_code = period_row['PeriodCode']
                    period_code_formatted = f"{week_type}{day_name_short}{period_code}"
                    period_node_data['period_code'] = period_code_formatted
                    period_node_data['path'] = timetable_period_path

                    academic_or_registration_period_of_day += 1

                period_node = period_node_class(**period_node_data)
                neon.create_or_merge_neontology_node(period_node, database=db_name, operation='merge')
                if isinstance(period_node, timetable_neo.AcademicPeriodNode) or isinstance(period_node, timetable_neo.RegistrationPeriodNode):
                    # Create the tldraw file for the node
                    fs_handler.create_default_tldraw_file(period_node.path, period_node.to_dict())
                timetable_nodes['academic_period_nodes'].append(period_node)
                logger.info(f'Created period node: {period_node.unique_id}')

                relationship_class = {
                    'Academic': tt_rels.AcademicDayHasAcademicPeriod,
                    'Registration': tt_rels.AcademicDayHasRegistrationPeriod,
                    'Break': tt_rels.AcademicDayHasBreakPeriod,
                    'OffTimetable': tt_rels.AcademicDayHasOffTimetablePeriod
                }[period_row['PeriodType']]

                neon.create_or_merge_neontology_relationship(
                    relationship_class(source=day_node, target=period_node),
                    database=db_name, operation='merge'
                )
                logger.info(f"Created relationship from {day_node.unique_id} to {period_node.unique_id}")
                period_of_day += 1 # We don't use this but we could
            academic_day_number += 1 # This is a bit of a hack but it works to keep the directories aligned (reorganise)
        day_number += 1 # We don't use this but we could

    def create_school_timetable_node_sequence_rels(timetable_nodes):
        def sort_and_create_relationships(nodes, relationship_map, sort_key):
            sorted_nodes = sorted(nodes, key=sort_key)
            for i in range(len(sorted_nodes) - 1):
                source_node = sorted_nodes[i]
                target_node = sorted_nodes[i + 1]
                node_type_pair = (type(source_node), type(target_node))
                relationship_class = relationship_map.get(node_type_pair)
                if relationship_class:
                    # Avoid self-referential relationships
                    if source_node.unique_id != target_node.unique_id:
                        neon.create_or_merge_neontology_relationship(
                            relationship_class(
                                source=source_node,
                                target=target_node
                            ),
                            database=db_name, operation='merge'
                        )
                        logger.info(f"Created relationship from {source_node.unique_id} to {target_node.unique_id}")
                    else:
                        logger.warning(f"Skipped self-referential relationship for node {source_node.unique_id}")

        # Relationship maps for different node types
        academic_year_relationship_map = {
            (timetable_neo.AcademicYearNode, timetable_neo.AcademicYearNode): tt_rels.AcademicYearFollowsAcademicYear
        }

        academic_term_relationship_map = {
            (timetable_neo.AcademicTermNode, timetable_neo.AcademicTermBreakNode): tt_rels.AcademicTermBreakFollowsAcademicTerm,
            (timetable_neo.AcademicTermBreakNode, timetable_neo.AcademicTermNode): tt_rels.AcademicTermFollowsAcademicTermBreak
        }

        academic_week_relationship_map = {
            (timetable_neo.AcademicWeekNode, timetable_neo.AcademicWeekNode): tt_rels.AcademicWeekFollowsAcademicWeek,
            (timetable_neo.HolidayWeekNode, timetable_neo.HolidayWeekNode): tt_rels.HolidayWeekFollowsHolidayWeek,
            (timetable_neo.AcademicWeekNode, timetable_neo.HolidayWeekNode): tt_rels.HolidayWeekFollowsAcademicWeek,
            (timetable_neo.HolidayWeekNode, timetable_neo.AcademicWeekNode): tt_rels.AcademicWeekFollowsHolidayWeek
        }

        academic_day_relationship_map = {
            (timetable_neo.AcademicDayNode, timetable_neo.AcademicDayNode): tt_rels.AcademicDayFollowsAcademicDay,
            (timetable_neo.HolidayDayNode, timetable_neo.HolidayDayNode): tt_rels.HolidayDayFollowsHolidayDay,
            (timetable_neo.OffTimetableDayNode, timetable_neo.OffTimetableDayNode): tt_rels.OffTimetableDayFollowsOffTimetableDay,
            (timetable_neo.StaffDayNode, timetable_neo.StaffDayNode): tt_rels.StaffDayFollowsStaffDay,

            (timetable_neo.AcademicDayNode, timetable_neo.HolidayDayNode): tt_rels.HolidayDayFollowsAcademicDay,
            (timetable_neo.AcademicDayNode, timetable_neo.OffTimetableDayNode): tt_rels.OffTimetableDayFollowsAcademicDay,
            (timetable_neo.AcademicDayNode, timetable_neo.StaffDayNode): tt_rels.StaffDayFollowsAcademicDay,

            (timetable_neo.HolidayDayNode, timetable_neo.AcademicDayNode): tt_rels.AcademicDayFollowsHolidayDay,
            (timetable_neo.HolidayDayNode, timetable_neo.OffTimetableDayNode): tt_rels.OffTimetableDayFollowsHolidayDay,
            (timetable_neo.HolidayDayNode, timetable_neo.StaffDayNode): tt_rels.StaffDayFollowsHolidayDay,

            (timetable_neo.OffTimetableDayNode, timetable_neo.AcademicDayNode): tt_rels.AcademicDayFollowsOffTimetableDay,
            (timetable_neo.OffTimetableDayNode, timetable_neo.HolidayDayNode): tt_rels.HolidayDayFollowsOffTimetableDay,
            (timetable_neo.OffTimetableDayNode, timetable_neo.StaffDayNode): tt_rels.StaffDayFollowsOffTimetableDay,

            (timetable_neo.StaffDayNode, timetable_neo.AcademicDayNode): tt_rels.AcademicDayFollowsStaffDay,
            (timetable_neo.StaffDayNode, timetable_neo.HolidayDayNode): tt_rels.HolidayDayFollowsStaffDay,
            (timetable_neo.StaffDayNode, timetable_neo.OffTimetableDayNode): tt_rels.OffTimetableDayFollowsStaffDay,
        }

        academic_period_relationship_map = {
            (timetable_neo.AcademicPeriodNode, timetable_neo.AcademicPeriodNode): tt_rels.AcademicPeriodFollowsAcademicPeriod,
            (timetable_neo.AcademicPeriodNode, timetable_neo.BreakPeriodNode): tt_rels.BreakPeriodFollowsAcademicPeriod,
            (timetable_neo.AcademicPeriodNode, timetable_neo.RegistrationPeriodNode): tt_rels.RegistrationPeriodFollowsAcademicPeriod,
            (timetable_neo.AcademicPeriodNode, timetable_neo.OffTimetablePeriodNode): tt_rels.OffTimetablePeriodFollowsAcademicPeriod,
            (timetable_neo.BreakPeriodNode, timetable_neo.AcademicPeriodNode): tt_rels.AcademicPeriodFollowsBreakPeriod,
            (timetable_neo.BreakPeriodNode, timetable_neo.BreakPeriodNode): tt_rels.BreakPeriodFollowsBreakPeriod,
            (timetable_neo.BreakPeriodNode, timetable_neo.RegistrationPeriodNode): tt_rels.RegistrationPeriodFollowsBreakPeriod,
            (timetable_neo.BreakPeriodNode, timetable_neo.OffTimetablePeriodNode): tt_rels.OffTimetablePeriodFollowsBreakPeriod,
            (timetable_neo.RegistrationPeriodNode, timetable_neo.AcademicPeriodNode): tt_rels.AcademicPeriodFollowsRegistrationPeriod,
            (timetable_neo.RegistrationPeriodNode, timetable_neo.RegistrationPeriodNode): tt_rels.RegistrationPeriodFollowsRegistrationPeriod,
            (timetable_neo.RegistrationPeriodNode, timetable_neo.BreakPeriodNode): tt_rels.BreakPeriodFollowsRegistrationPeriod,
            (timetable_neo.RegistrationPeriodNode, timetable_neo.OffTimetablePeriodNode): tt_rels.OffTimetablePeriodFollowsRegistrationPeriod,
            (timetable_neo.OffTimetablePeriodNode, timetable_neo.OffTimetablePeriodNode): tt_rels.OffTimetablePeriodFollowsOffTimetablePeriod,
            (timetable_neo.OffTimetablePeriodNode, timetable_neo.AcademicPeriodNode): tt_rels.AcademicPeriodFollowsOffTimetablePeriod,
            (timetable_neo.OffTimetablePeriodNode, timetable_neo.BreakPeriodNode): tt_rels.BreakPeriodFollowsOffTimetablePeriod,
            (timetable_neo.OffTimetablePeriodNode, timetable_neo.RegistrationPeriodNode): tt_rels.RegistrationPeriodFollowsOffTimetablePeriod,
        }


        # Sort and create relationships
        sort_and_create_relationships(timetable_nodes['academic_year_nodes'], academic_year_relationship_map, lambda x: int(x.year))
        sort_and_create_relationships(timetable_nodes['academic_term_nodes'], academic_term_relationship_map, lambda x: x.start_date)
        sort_and_create_relationships(timetable_nodes['academic_week_nodes'], academic_week_relationship_map, lambda x: x.start_date)
        sort_and_create_relationships(timetable_nodes['academic_day_nodes'], academic_day_relationship_map, lambda x: x.date)
        sort_and_create_relationships(timetable_nodes['academic_period_nodes'], academic_period_relationship_map, lambda x: (x.start_time, x.end_time))

    # Call the function with the created timetable nodes
    create_school_timetable_node_sequence_rels(timetable_nodes)

    logger.info(f'Created timetable: {timetable_nodes["timetable_node"].unique_id}')

    # Log the directory structure after creation
    # root_timetable_directory = fs_handler.root_path  # Access the root directory of the filesystem handler
    # fs_handler.log_directory_structure(root_timetable_directory)

    return {
        'school_node': school_node,
        'school_calendar_nodes': calendar_nodes,
        'school_timetable_nodes': timetable_nodes
    }