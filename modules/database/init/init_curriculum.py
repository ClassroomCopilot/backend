from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_init_curriculum'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import modules.database.schemas.curriculum_neo as neo_curriculum
import modules.database.schemas.relationships.curricular_relationships as curricular_relationships
import modules.database.schemas.relationships.entity_curriculum_rels as ent_cur_rels
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
import modules.database.tools.neontology_tools as neon
import pandas as pd

def create_curriculum(dataframes, db_name, school_node):
    
    fs_handler = ClassroomCopilotFilesystem(db_name, init_run_type="school")
    
    logging.info(f"Initialising neo4j connection...")
    neon.init_neontology_connection()
    
    keystagesyllabus_df = dataframes['keystagesyllabuses']
    yeargroupsyllabus_df = dataframes['yeargroupsyllabuses']
    topic_df = dataframes['topics']
    lesson_df = dataframes['lessons']
    statement_df = dataframes['statements']
    # resource_df = dataframes['resources'] # TODO
    
    node_library = {}
    node_library['key_stage_nodes'] = {}
    node_library['year_group_nodes'] = {}
    node_library['key_stage_syllabus_nodes'] = {}
    node_library['year_group_syllabus_nodes'] = {}
    node_library['topic_nodes'] = {}
    node_library['topic_lesson_nodes'] = {}
    node_library['statement_nodes'] = {}
    curriculum_node = None
    pastoral_node = None
    key_stage_nodes_created = {}
    year_group_nodes_created = {}
    last_year_group_node = {}
    last_key_stage_node = None
    
    # Create Curriculum and Pastoral nodes and relationships with School
    _, curriculum_path = fs_handler.create_school_curriculum_directory(school_node.path)
    _, pastoral_path = fs_handler.create_school_pastoral_directory(school_node.path)
    curriculum_structure_node_unique_id = f"CurriculumStructure_{school_node.unique_id}"
    curriculum_node = neo_curriculum.CurriculumStructureNode(
        unique_id=curriculum_structure_node_unique_id,
        path=curriculum_path
    )
    neon.create_or_merge_neontology_node(curriculum_node, database=db_name, operation='merge')
    # Create the tldraw file for the node
    fs_handler.create_default_tldraw_file(curriculum_node.path, curriculum_node.to_dict())
    node_library['curriculum_node'] = curriculum_node
    neon.create_or_merge_neontology_relationship(
        ent_cur_rels.SchoolHasCurriculumStructure(source=school_node, target=curriculum_node),
        database=db_name, operation='merge'
    )
    logging.info(f"Created curriculum node and relationship with school")
    
    pastoral_structure_node_unique_id = f"PastoralStructure_{school_node.unique_id}"
    pastoral_node = neo_curriculum.PastoralStructureNode(
        unique_id=pastoral_structure_node_unique_id,
        path=pastoral_path
    )
    neon.create_or_merge_neontology_node(pastoral_node, database=db_name, operation='merge')
    # Create the tldraw file for the node
    fs_handler.create_default_tldraw_file(pastoral_node.path, pastoral_node.to_dict())
    node_library['pastoral_node'] = pastoral_node
    neon.create_or_merge_neontology_relationship(
        ent_cur_rels.SchoolHasPastoralStructure(source=school_node, target=pastoral_node),
        database=db_name, operation='merge'
    )
    logging.info(f"Created pastoral node and relationship with school")
    
    default_topic_values = {
        'topic_assessment_type': 'Null',
        'topic_type': 'Null',
        'total_number_of_lessons_for_topic': '1',
        'topic_title': 'Null'
    }

    default_topic_lesson_values = {
        'topic_lesson_title': 'Null',
        'topic_lesson_type': 'Null',
        'topic_lesson_length': '1',
        'topic_lesson_suggested_activities': 'Null',
        'topic_lesson_skills_learned': 'Null',
        'topic_lesson_weblinks': 'Null',
    }

    default_learning_statement_values = {
        'lesson_learning_statement': 'Null',
        'lesson_learning_statement_type': 'Student learning outcome'
    }

    # Function to sort year groups numerically where possible
    def sort_year_groups(df):
        df = df.copy()
        df['YearGroupNumeric'] = pd.to_numeric(df['YearGroup'], errors='coerce')
        return df.sort_values(by='YearGroupNumeric')
    
    logging.info(f"Processing key stages")
    for index, ks_row in keystagesyllabus_df.sort_values('KeyStage').iterrows():
        key_stage = str(ks_row['KeyStage'])
        _, key_stage_path = fs_handler.create_school_curriculum_key_stage_directory(curriculum_path, key_stage)
        if key_stage not in key_stage_nodes_created:
            key_stage_node_unique_id = f"KeyStage_{curriculum_node.unique_id}_KStg{key_stage}"
            key_stage_node = neo_curriculum.KeyStageNode(
                unique_id=key_stage_node_unique_id,
                key_stage_name=f"Key Stage {key_stage}",
                key_stage=str(key_stage),
                path=key_stage_path
            )
            neon.create_or_merge_neontology_node(key_stage_node, database=db_name, operation='merge')
            # Create the tldraw file for the node
            fs_handler.create_default_tldraw_file(key_stage_node.path, key_stage_node.to_dict())
            key_stage_nodes_created[key_stage] = key_stage_node
            node_library['key_stage_nodes'][key_stage] = key_stage_node
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.CurriculumStructureIncludesKeyStage(source=curriculum_node, target=key_stage_node),
                database=db_name, operation='merge'
            )
            logging.info(f"Created key stage node {key_stage_node_unique_id} and relationship with curriculum structure {curriculum_structure_node_unique_id}")

            if last_key_stage_node:
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.KeyStageFollowsKeyStage(source=last_key_stage_node, target=key_stage_node),
                    database=db_name, operation='merge'
                )
                logging.info(f"Created relationship between key stages {last_key_stage_node.unique_id} and {key_stage_node.unique_id}")
            last_key_stage_node = key_stage_node

        _, key_stage_syllabus_path = fs_handler.create_school_curriculum_keystage_syllabus_directory(curriculum_path, key_stage, ks_row['ID'])
        logging.info(f"Created key stage syllabus directory for {key_stage_syllabus_path}")
        
        key_stage_syllabus_node_unique_id = f"KeyStageSyllabus_{curriculum_node.unique_id}_{ks_row['Title'].replace(' ', '')}"
        key_stage_syllabus_node = neo_curriculum.KeyStageSyllabusNode(
            unique_id=key_stage_syllabus_node_unique_id,
            ks_syllabus_id=ks_row['ID'],
            ks_syllabus_name=ks_row['Title'],
            ks_syllabus_key_stage=str(ks_row['KeyStage']),
            ks_syllabus_subject=ks_row['Subject'],
            ks_syllabus_subject_code=ks_row['SubjectCode'],
            path=key_stage_syllabus_path
        )
        neon.create_or_merge_neontology_node(key_stage_syllabus_node, database=db_name, operation='merge')
        # Create the tldraw file for the node
        fs_handler.create_default_tldraw_file(key_stage_syllabus_node.path, key_stage_syllabus_node.to_dict())
        node_library['key_stage_syllabus_nodes'][ks_row['ID']] = key_stage_syllabus_node
        neon.create_or_merge_neontology_relationship(
            curricular_relationships.KeyStageIncludesKeyStageSyllabus(source=key_stage_node, target=key_stage_syllabus_node),
            database=db_name,
            operation='merge'
        )
        logging.info(f"Created key stage syllabus node {key_stage_syllabus_node_unique_id} and relationship with key stage {key_stage_node_unique_id}")

        related_yeargroups = sort_year_groups(yeargroupsyllabus_df[yeargroupsyllabus_df['KeyStage'] == ks_row['KeyStage']])
        
        logging.info(f"Processing year groups for key stage {key_stage}")
        for yg_index, yg_row in related_yeargroups.iterrows():
            year_group = yg_row['YearGroup']
            numeric_year_group = pd.to_numeric(year_group, errors='coerce')

            if pd.notna(numeric_year_group):
                numeric_year_group = int(numeric_year_group)
                if numeric_year_group not in year_group_nodes_created:
                    _, year_group_path = fs_handler.create_school_curriculum_year_group_directory(curriculum_path, year_group)
                    logging.info(f"Created year group directory for {year_group_path}")
                    
                    year_group_node_unique_id = f"YearGroup_{school_node.unique_id}_YGrp{numeric_year_group}" # TODO: This unique id format does not make sense: maybe get the correct pastoral node
                    year_group_node = neo_curriculum.YearGroupNode(
                        unique_id=year_group_node_unique_id,
                        year_group=str(numeric_year_group),
                        year_group_name=f"Year {numeric_year_group}",
                        path=year_group_path
                    )
                    neon.create_or_merge_neontology_node(year_group_node, database=db_name, operation='merge')
                    # Create the tldraw file for the node
                    fs_handler.create_default_tldraw_file(year_group_node.path, year_group_node.to_dict())
                    # Create relationship with Pastoral Structure
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.PastoralStructureIncludesYearGroup(source=pastoral_node, target=year_group_node),
                        database=db_name, operation='merge'
                    )
                    logging.info(f"Created year group node {year_group_node_unique_id} and relationship with pastoral structure {pastoral_structure_node_unique_id}")
                    
                    year_group_nodes_created[numeric_year_group] = year_group_node
                    node_library['year_group_nodes'][str(numeric_year_group)] = year_group_node
                    # Create sequential relationships correctly
                    if numeric_year_group - 1 in last_year_group_node:
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.YearGroupFollowsYearGroup(source=last_year_group_node[numeric_year_group - 1], target=year_group_node),
                            database=db_name, operation='merge'
                        )
                        logging.info(f"Created relationship between year groups {last_year_group_node[numeric_year_group - 1].unique_id} and {year_group_node.unique_id}")
                    last_year_group_node[numeric_year_group] = year_group_node

            # Always create year group syllabus nodes
            _, year_group_syllabus_path = fs_handler.create_school_curriculum_year_group_syllabus_directory(curriculum_path, year_group, yg_row['ID'])
            logging.info(f"Created year group syllabus directory for {year_group_syllabus_path}")
            
            year_group_syllabus_node_unique_id = f"YearGroupSyllabus_{school_node.unique_id}_{yg_row['ID']}"
            year_group_syllabus_node = neo_curriculum.YearGroupSyllabusNode(
                unique_id=year_group_syllabus_node_unique_id,
                yr_syllabus_id=yg_row['ID'],
                yr_syllabus_name=yg_row['Title'],
                yr_syllabus_year_group=str(yg_row['YearGroup']),
                yr_syllabus_subject=yg_row['Subject'],
                yr_syllabus_subject_code=yg_row['SubjectCode'],
                path=year_group_syllabus_path
            )
            neon.create_or_merge_neontology_node(year_group_syllabus_node, database=db_name, operation='merge')
            # Create the tldraw file for the node
            fs_handler.create_default_tldraw_file(year_group_syllabus_node.path, year_group_syllabus_node.to_dict())
            node_library['year_group_syllabus_nodes'][yg_row['ID']] = year_group_syllabus_node
            logging.info(f"Created year group syllabus node {year_group_syllabus_node_unique_id} and relationship with key stage syllabus {key_stage_syllabus_node_unique_id}")
            
            if yg_row['Subject'] == ks_row['Subject']:
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.KeyStageSyllabusIncludesYearGroupSyllabus(source=key_stage_syllabus_node, target=year_group_syllabus_node),
                    database=db_name, operation='merge'
                )
                logging.info(f"Created relationship between key stage syllabus {key_stage_syllabus_node_unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")
            if pd.notna(numeric_year_group) and str(numeric_year_group) == str(year_group_node.year_group):
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.YearGroupHasYearGroupSyllabus(source=year_group_node, target=year_group_syllabus_node),
                    database=db_name, operation='merge'
                )
                logging.info(f"Created relationship between year group {year_group_node_unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")
    
    # Process topics, lessons, and statements
    logging.info(f"Processing topics, lessons, and statements")
    for index, topic_row in topic_df.iterrows():
        logging.debug(f"Processing topic {topic_row['TopicID']}")
        
        yr_syllabus_node = node_library['year_group_syllabus_nodes'].get(topic_row['SyllabusYearID']) # TODO: This is hacky
        logging.debug(f"Year group syllabus node: {yr_syllabus_node}")
        
        if yr_syllabus_node:
            logging.debug(f"Creating topic node for topic {topic_row['TopicID']}")
            _, topic_path = fs_handler.create_school_curriculum_topic_directory(curriculum_path, yr_syllabus_node.yr_syllabus_year_group, yr_syllabus_node.yr_syllabus_id, topic_row['TopicID'])
            logging.info(f"Created topic directory for {topic_path}")
            
            topic_node_unique_id = f"Topic_{yr_syllabus_node.unique_id}_{topic_row['TopicID']}"
            topic_node = neo_curriculum.TopicNode(
                unique_id=topic_node_unique_id,
                topic_id=topic_row['TopicID'],
                topic_title=topic_row.get('TopicTitle', default_topic_values['topic_title']),
                total_number_of_lessons_for_topic=str(topic_row.get('TotalNumberOfLessonsForTopic', default_topic_values['total_number_of_lessons_for_topic'])),
                topic_type=topic_row.get('TopicType', default_topic_values['topic_type']),
                topic_assessment_type=topic_row.get('TopicAssessmentType', default_topic_values['topic_assessment_type']),
                path=topic_path
            )
            neon.create_or_merge_neontology_node(topic_node, database=db_name, operation='merge')
            # Create the tldraw file for the node
            fs_handler.create_default_tldraw_file(topic_node.path, topic_node.to_dict())
            node_library['topic_nodes'][topic_row['TopicID']] = topic_node
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.TopicPartOfYearGroupSyllabus(source=yr_syllabus_node, target=topic_node),
                database=db_name, operation='merge'
            )
            logging.info(f"Created topic node {topic_node_unique_id} and relationship with year group syllabus {yr_syllabus_node.unique_id}")
            # TODO: Create suggested sequence relationships between topics

            lessons_df = lesson_df[lesson_df['TopicID'] == topic_row['TopicID']].copy()
            lessons_df.loc[:, 'Lesson'] = lessons_df['Lesson'].astype(str)
            lessons_df = lessons_df.sort_values('Lesson')

            previous_lesson_node = None
            for lesson_index, lesson_row in lessons_df.iterrows():
                _, lesson_path = fs_handler.create_school_curriculum_lesson_directory(curriculum_path, yr_syllabus_node.yr_syllabus_year_group, yr_syllabus_node.yr_syllabus_id, topic_row['TopicID'], lesson_row['Lesson'])
                logging.info(f"Created lesson directory for {lesson_path}")
                lesson_data = {
                    'unique_id': f"TopicLesson_{topic_node.unique_id}_{lesson_row['LessonID']}",
                    'topic_lesson_id': lesson_row['LessonID'],
                    'topic_lesson_title': lesson_row.get('LessonTitle', default_topic_lesson_values['topic_lesson_title']),
                    'topic_lesson_type': lesson_row.get('LessonType', default_topic_lesson_values['topic_lesson_type']),
                    'topic_lesson_length': str(lesson_row.get('SuggestedNumberOfPeriodsForLesson', default_topic_lesson_values['topic_lesson_length'])),
                    'topic_lesson_suggested_activities': lesson_row.get('SuggestedActivities', default_topic_lesson_values['topic_lesson_suggested_activities']),
                    'topic_lesson_skills_learned': lesson_row.get('SkillsLearned', default_topic_lesson_values['topic_lesson_skills_learned']),
                    'topic_lesson_weblinks': lesson_row.get('WebLinks', default_topic_lesson_values['topic_lesson_weblinks']),
                    'path': lesson_path
                }
                for key, value in lesson_data.items():
                    if pd.isna(value):
                        lesson_data[key] = default_topic_lesson_values[key]

                lesson_node = neo_curriculum.TopicLessonNode(**lesson_data)
                neon.create_or_merge_neontology_node(lesson_node, database=db_name, operation='merge')
                # Create the tldraw file for the node
                fs_handler.create_default_tldraw_file(lesson_node.path, lesson_node.to_dict())
                node_library['topic_lesson_nodes'][lesson_row['LessonID']] = lesson_node
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.TopicIncludesTopicLesson(source=topic_node, target=lesson_node),
                    database=db_name, operation='merge'
                )
                logging.info(f"Created lesson node {lesson_node.unique_id} and relationship with topic {topic_node.unique_id}")
                
                # Create sequential relationships if the lesson number is a digit
                # TODO: Handle non-digit lessons, e.g., R, F and T
                if lesson_row['Lesson'].isdigit() and previous_lesson_node:
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.TopicLessonFollowsTopicLesson(source=previous_lesson_node, target=lesson_node),
                        database=db_name, operation='merge'
                    )
                    logging.info(f"Created relationship between lesson {previous_lesson_node.unique_id} and {lesson_node.unique_id}")
                previous_lesson_node = lesson_node

                # Process each learning statement related to the lesson
                for statement_index, statement_row in statement_df[statement_df['LessonID'] == lesson_row['LessonID']].iterrows():
                    _, statement_path = fs_handler.create_school_curriculum_lesson_learning_statement_directory(curriculum_path, yr_syllabus_node.yr_syllabus_year_group, yr_syllabus_node.yr_syllabus_id, topic_row['TopicID'], lesson_row['Lesson'], statement_row['StatementID'])
                    statement_data = {
                        'unique_id': f"LearningStatement_{lesson_node.unique_id}_{statement_row['StatementID']}",
                        'lesson_learning_statement_id': statement_row['StatementID'],
                        'lesson_learning_statement': statement_row.get('LearningStatement', default_learning_statement_values['lesson_learning_statement']),
                        'lesson_learning_statement_type': statement_row.get('StatementType', default_learning_statement_values['lesson_learning_statement_type']),
                        'path': statement_path
                    }
                    for key in statement_data:
                        if pd.isna(statement_data[key]):
                            statement_data[key] = default_learning_statement_values[key]

                    statement_node = neo_curriculum.LearningStatementNode(**statement_data)
                    neon.create_or_merge_neontology_node(statement_node, database=db_name, operation='merge')
                    # Create the tldraw file for the node
                    fs_handler.create_default_tldraw_file(statement_node.path, statement_node.to_dict())
                    node_library['statement_nodes'][statement_row['StatementID']] = statement_node
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.LessonIncludesLearningStatement(source=lesson_node, target=statement_node),
                        database=db_name, operation='merge'
                    )
                    logging.info(f"Created learning statement node {statement_node.unique_id} and relationship with lesson {lesson_node.unique_id}")
                # TODO: Lesson has Science Lab
    return node_library