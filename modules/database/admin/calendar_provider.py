import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

import modules.database.schemas.calendar_neo as calendar_neo
import modules.database.schemas.entity_neo as entity_neo
import modules.database.schemas.relationships.calendar_rels as cal_rels
import modules.database.tools.neontology_tools as neon
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from datetime import timedelta, datetime

def create_calendar(db_name, start_date, end_date, attach_to_calendar_node=False, entity_node=None, time_chunk_node=None):
    logger.info(f"Creating calendar for {start_date} to {end_date}")

    logger.info("Initializing Neontology connection")

    neon.init_neontology_connection()

    filesystem = ClassroomCopilotFilesystem(db_name, init_run_type="school")

    def create_tldraw_file_for_node(node, node_path):
        node_data = {
            "unique_id": node.unique_id,
            "type": node.__class__.__name__,
            "name": node.name if hasattr(node, 'name') else 'Unnamed Node'
        }
        logger.debug(f"Creating tldraw file for node: {node_data}")
        filesystem.create_default_tldraw_file(node_path, node_data)

    created_years = {}
    created_months = {}
    created_weeks = {}
    created_days = {}

    last_year_node = None
    last_month_node = None
    last_week_node = None
    last_day_node = None

    calendar_nodes = {
        'calendar_node': None,
        'calendar_year_nodes': [],
        'calendar_month_nodes': [],
        'calendar_week_nodes': [],
        'calendar_day_nodes': []
    }

    calendar_type = None
    if attach_to_calendar_node and entity_node:
        calendar_type = "entity_calendar"
        logger.info(f"Attaching calendar to entity node: {entity_node.unique_id}")
        entity_unique_id = entity_node.unique_id
        calendar_unique_id = f"Calendar_{entity_unique_id}"
        calendar_name = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        calendar_path = os.path.join(entity_node.path, "calendar")
        calendar_node = calendar_neo.CalendarNode(
            unique_id=calendar_unique_id,
            name=calendar_name,
            start_date=start_date,
            end_date=end_date,
            path=calendar_path
        )
        neon.create_or_merge_neontology_node(calendar_node, database=db_name, operation='merge')
        calendar_nodes['calendar_node'] = calendar_node
        logger.info(f"Calendar node created: {calendar_node.unique_id}")

        # Create a node tldraw file for the calendar node
        create_tldraw_file_for_node(calendar_node, calendar_path)

        import modules.database.schemas.relationships.entity_calendar_rels as entity_cal_rels

        neon.create_or_merge_neontology_relationship(
            entity_cal_rels.EntityHasCalendar(source=entity_node, target=calendar_node),
            database=db_name,
            operation='merge'
        )
        logger.info(f"Relationship created from {entity_node.unique_id} to {calendar_node.unique_id}")
    if entity_node and not attach_to_calendar_node:
        calendar_type = "time_entity"
    else:
        logger.error("Invalid combination of parameters for calendar creation.")
        raise ValueError("Invalid combination of parameters for calendar creation.")

    current_date = start_date
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        iso_year, iso_week, iso_weekday = current_date.isocalendar()

        # Create directories for year, month, week, and day
        _, year_path = filesystem.create_year_directory(year, calendar_path)
        _, month_path = filesystem.create_month_directory(year, month, calendar_path)
        _, week_path = filesystem.create_week_directory(year, iso_week, calendar_path)
        _, day_path = filesystem.create_day_directory(year, month, day, calendar_path)

        calendar_year_unique_id = f"CalendarYear_{year}"

        if year not in created_years:
            year_node = calendar_neo.CalendarYearNode(
                unique_id=calendar_year_unique_id,
                year=str(year),
                path=year_path
            )
            neon.create_or_merge_neontology_node(year_node, database=db_name, operation='merge')
            calendar_nodes['calendar_year_nodes'].append(year_node)
            created_years[year] = year_node
            create_tldraw_file_for_node(year_node, year_path)
            logger.info(f"Year node created: {year_node.unique_id}")

            if attach_to_calendar_node:
                neon.create_or_merge_neontology_relationship(
                    cal_rels.CalendarIncludesYear(source=calendar_node, target=year_node),
                    database=db_name,
                    operation='merge'
                )
                logger.info(f"Relationship created from {calendar_node.unique_id} to {year_node.unique_id}")
            if last_year_node:
                neon.create_or_merge_neontology_relationship(
                    cal_rels.YearFollowsYear(source=last_year_node, target=year_node),
                    database=db_name,
                    operation='merge'
                )
                logger.info(f"Relationship created from {last_year_node.unique_id} to {year_node.unique_id}")
            last_year_node = year_node

        calendar_month_unique_id = f"CalendarMonth_{year}_{month}"

        month_key = f"{year}-{month}"
        if month_key not in created_months:
            month_node = calendar_neo.CalendarMonthNode(
                unique_id=calendar_month_unique_id,
                year=str(year),
                month=str(month),
                month_name=datetime(year, month, 1).strftime('%B'),
                path=month_path
            )
            neon.create_or_merge_neontology_node(month_node, database=db_name, operation='merge')
            calendar_nodes['calendar_month_nodes'].append(month_node)
            created_months[month_key] = month_node
            create_tldraw_file_for_node(month_node, month_path)
            logger.info(f"Month node created: {month_node.unique_id}")

            # Check for the end of year transition for months
            if last_month_node:
                if int(month) == 1 and int(last_month_node.month) == 12 and int(last_month_node.year) == year - 1:
                    neon.create_or_merge_neontology_relationship(
                        cal_rels.MonthFollowsMonth(source=last_month_node, target=month_node),
                        database=db_name,
                        operation='merge'
                    )
                    logger.info(f"Relationship created from {last_month_node.unique_id} to {month_node.unique_id}")
                elif int(month) == int(last_month_node.month) + 1:
                    neon.create_or_merge_neontology_relationship(
                        cal_rels.MonthFollowsMonth(source=last_month_node, target=month_node),
                        database=db_name,
                        operation='merge'
                    )
                    logger.info(f"Relationship created from {last_month_node.unique_id} to {month_node.unique_id}")
            last_month_node = month_node

            neon.create_or_merge_neontology_relationship(
                cal_rels.YearIncludesMonth(source=year_node, target=month_node),
                database=db_name,
                operation='merge'
            )
            logger.info(f"Relationship created from {year_node.unique_id} to {month_node.unique_id}")
       
        calendar_week_unique_id = f"CalendarWeek_{iso_year}_{iso_week}"
        
        week_key = f"{iso_year}-W{iso_week}"
        if week_key not in created_weeks:
            # Get the date of the first monday of the week
            week_start_date = current_date - timedelta(days=current_date.weekday())
            week_node = calendar_neo.CalendarWeekNode(
                unique_id=calendar_week_unique_id,
                start_date=week_start_date,
                week_number=str(iso_week),
                iso_week=f"{iso_year}-W{iso_week:02}",
                path=week_path
            )
            neon.create_or_merge_neontology_node(week_node, database=db_name, operation='merge')
            calendar_nodes['calendar_week_nodes'].append(week_node)
            created_weeks[week_key] = week_node
            create_tldraw_file_for_node(week_node, week_path)
            logger.info(f"Week node created: {week_node.unique_id}")

            if last_week_node and ((last_week_node.iso_week.split('-')[0] == str(iso_year) and int(last_week_node.week_number) == int(iso_week) - 1) or
                                (last_week_node.iso_week.split('-')[0] != str(iso_year) and int(last_week_node.week_number) == 52 and int(iso_week) == 1)):
                neon.create_or_merge_neontology_relationship(
                    cal_rels.WeekFollowsWeek(source=last_week_node, target=week_node),
                    database=db_name,
                    operation='merge'
                )
                logger.info(f"Relationship created from {last_week_node.unique_id} to {week_node.unique_id}")
            last_week_node = week_node

            neon.create_or_merge_neontology_relationship(
                cal_rels.YearIncludesWeek(source=year_node, target=week_node),
                database=db_name,
                operation='merge'
            )
            logger.info(f"Relationship created from {year_node.unique_id} to {week_node.unique_id}")

        calendar_day_unique_id = f"CalendarDay_{year}_{month}_{day}"
            
        day_key = f"{year}-{month}-{day}"
        day_node = calendar_neo.CalendarDayNode(
            unique_id=calendar_day_unique_id,
            date=current_date,
            day_of_week=current_date.strftime('%A'),
            iso_day=f"{year}-{month:02}-{day:02}",
            path=day_path
        )
        neon.create_or_merge_neontology_node(day_node, database=db_name, operation='merge')
        calendar_nodes['calendar_day_nodes'].append(day_node)
        created_days[day_key] = day_node
        create_tldraw_file_for_node(day_node, day_path)
        logger.info(f"Day node created: {day_node.unique_id}")

        if last_day_node:
            neon.create_or_merge_neontology_relationship(
                cal_rels.DayFollowsDay(source=last_day_node, target=day_node),
                database=db_name,
                operation='merge'
            )
            logger.info(f"Relationship created from {last_day_node.unique_id} to {day_node.unique_id}")
        last_day_node = day_node

        neon.create_or_merge_neontology_relationship(
            cal_rels.MonthIncludesDay(source=month_node, target=day_node),
            database=db_name,
            operation='merge'
        )
        logger.info(f"Relationship created from {month_node.unique_id} to {day_node.unique_id}")
        neon.create_or_merge_neontology_relationship(
            cal_rels.WeekIncludesDay(source=week_node, target=day_node),
            database=db_name,
            operation='merge'
        )
        logger.info(f"Relationship created from {week_node.unique_id} to {day_node.unique_id}")
        current_date += timedelta(days=1)

    if time_chunk_node:
        time_chunk_interval = time_chunk_node
        # Get every calendar day node and create time chunks of length time_chunk_node minutes for the whole day
        for day_node in calendar_nodes['calendar_day_nodes']:
            day_path = day_node.path
            total_time_chunks_in_day = (24 * 60) / time_chunk_interval
            for i in range(total_time_chunks_in_day):
                time_chunk_unique_id = f"CalendarTimeChunk_{day_node.unique_id}_{i}"
                time_chunk_start_time = day_node.date.time() + timedelta(minutes=i * time_chunk_interval)
                time_chunk_end_time = time_chunk_start_time + timedelta(minutes=time_chunk_interval)
                time_chunk_node = calendar_neo.CalendarTimeChunkNode(
                    unique_id=time_chunk_unique_id,
                    start_time=time_chunk_start_time,
                    end_time=time_chunk_end_time,
                    path=day_path
                )
                neon.create_or_merge_neontology_node(time_chunk_node, database=db_name, operation='merge')
                calendar_nodes['calendar_time_chunk_nodes'].append(time_chunk_node)
                logger.info(f"Time chunk node created: {time_chunk_node.unique_id}")
                # Create a relationship between the time chunk node and the day node
                neon.create_or_merge_neontology_relationship(
                    cal_rels.DayIncludesTimeChunk(source=day_node, target=time_chunk_node),
                    database=db_name,
                    operation='merge'
                )
                logger.info(f"Relationship created from {day_node.unique_id} to {time_chunk_node.unique_id}")
                # Create sequential relationship between the time chunk nodes
                if i > 0:
                    neon.create_or_merge_neontology_relationship(
                        cal_rels.TimeChunkFollowsTimeChunk(source=calendar_nodes['calendar_time_chunk_nodes'][i-1], target=time_chunk_node),
                        database=db_name,
                        operation='merge'
                    )
                    logger.info(f"Relationship created from {calendar_nodes['calendar_time_chunk_nodes'][i-1].unique_id} to {time_chunk_node.unique_id}")

    logger.info(f'Created calendar: {calendar_nodes["calendar_node"].unique_id}')
    return calendar_nodes