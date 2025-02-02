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
import modules.database.schemas.entity_neo as neo_entity
import modules.database.schemas.curriculum_neo as neo_curriculum
import modules.database.schemas.relationships.curricular_relationships as curricular_relationships
import modules.database.schemas.relationships.entity_relationships as ent_rels
import modules.database.schemas.relationships.entity_curriculum_rels as ent_cur_rels
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
import modules.database.tools.neontology_tools as neon
import pandas as pd

# Default values for nodes
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

# Helper function to sort year groups numerically where possible
def sort_year_groups(df):
    df = df.copy()
    df['YearGroupNumeric'] = pd.to_numeric(df['YearGroup'], errors='coerce')
    return df.sort_values(by='YearGroupNumeric')

def create_curriculum(dataframes, db_name, curriculum_db_name, school_node):
    
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
    node_library['department_nodes'] = {}
    node_library['subject_nodes'] = {}
    curriculum_node = None
    pastoral_node = None
    key_stage_nodes_created = {}
    year_group_nodes_created = {}
    last_year_group_node = None
    last_key_stage_node = None
    
    # Create Curriculum and Pastoral nodes and relationships with School in both databases
    _, curriculum_path = fs_handler.create_school_curriculum_directory(school_node.path)
    _, pastoral_path = fs_handler.create_school_pastoral_directory(school_node.path)
    
    # Create Department Structure node
    department_structure_node_unique_id = f"DepartmentStructure_{school_node.unique_id}"
    department_structure_node = neo_entity.DepartmentStructureNode(
        unique_id=department_structure_node_unique_id,
        path=os.path.join(school_node.path, "departments")
    )
    # Create in school database only
    neon.create_or_merge_neontology_node(department_structure_node, database=db_name, operation='merge')
    fs_handler.create_default_tldraw_file(department_structure_node.path, department_structure_node.to_dict())
    node_library['department_structure_node'] = department_structure_node
    
    # Link Department Structure to School
    neon.create_or_merge_neontology_relationship(
        ent_rels.SchoolHasDepartmentStructure(source=school_node, target=department_structure_node),
        database=db_name, operation='merge'
    )
    logging.info(f"Created department structure node and linked to school")
    
    curriculum_structure_node_unique_id = f"CurriculumStructure_{school_node.unique_id}"
    curriculum_node = neo_curriculum.CurriculumStructureNode(
        unique_id=curriculum_structure_node_unique_id,
        path=curriculum_path
    )
    # Create in school database only
    neon.create_or_merge_neontology_node(curriculum_node, database=db_name, operation='merge')
    fs_handler.create_default_tldraw_file(curriculum_node.path, curriculum_node.to_dict())
    node_library['curriculum_node'] = curriculum_node
    
    # Create relationship in school database only
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
    fs_handler.create_default_tldraw_file(pastoral_node.path, pastoral_node.to_dict())
    node_library['pastoral_node'] = pastoral_node
    neon.create_or_merge_neontology_relationship(
        ent_cur_rels.SchoolHasPastoralStructure(source=school_node, target=pastoral_node),
        database=db_name, operation='merge'
    )
    logging.info(f"Created pastoral node and relationship with school")
    
    # Create departments and subjects
    # First get unique departments
    unique_departments = keystagesyllabus_df['Department'].dropna().unique()
    
    for department_name in unique_departments:
        department_unique_id = f"Department_{school_node.unique_id}_{department_name.replace(' ', '_')}"
        _, department_path = fs_handler.create_school_department_directory(school_node.path, department_name)
        
        department_node = neo_entity.DepartmentNode(
            unique_id=department_unique_id,
            department_name=department_name,
            path=department_path
        )
        # Create department in school database only
        neon.create_or_merge_neontology_node(department_node, database=db_name, operation='merge')
        fs_handler.create_default_tldraw_file(department_node.path, department_node.to_dict())
        node_library['department_nodes'][department_name] = department_node
        
        # Link department to department structure in school database
        neon.create_or_merge_neontology_relationship(
            ent_rels.DepartmentStructureHasDepartment(source=department_structure_node, target=department_node),
            database=db_name, operation='merge'
        )
        logging.info(f"Created department node for {department_name} and linked to department structure")
    
    # Create subjects and link to departments
    # First get unique subjects from key stage syllabuses (which have department info)
    unique_subjects = keystagesyllabus_df[['Subject', 'SubjectCode', 'Department']].drop_duplicates()
    
    # Then add any additional subjects from year group syllabuses (without department info)
    additional_subjects = yeargroupsyllabus_df[['Subject', 'SubjectCode']].drop_duplicates()
    additional_subjects = additional_subjects[~additional_subjects['SubjectCode'].isin(unique_subjects['SubjectCode'])]
    
    # Process subjects from key stage syllabuses first (these have department info)
    for _, subject_row in unique_subjects.iterrows():
        subject_unique_id = f"Subject_{school_node.unique_id}_{subject_row['SubjectCode']}"
        department_node = node_library['department_nodes'].get(subject_row['Department'])
        if not department_node:
            logging.warning(f"No department found for subject {subject_row['Subject']} with code {subject_row['SubjectCode']}")
            continue
            
        _, subject_path = fs_handler.create_department_subject_directory(
            department_node.path,
            subject_row['Subject']  # Use full subject name instead of SubjectCode
        )
        logging.info(f"Created subject directory for {subject_path}")
        
        subject_node = neo_curriculum.SubjectNode(
            unique_id=subject_unique_id,
            subject_code=subject_row['SubjectCode'],
            subject_name=subject_row['Subject'],
            path=subject_path
        )
        # Create subject in both databases
        neon.create_or_merge_neontology_node(subject_node, database=db_name, operation='merge')
        neon.create_or_merge_neontology_node(subject_node, database=curriculum_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(subject_node.path, subject_node.to_dict())
        node_library['subject_nodes'][subject_row['Subject']] = subject_node
        
        # Link subject to department in school database only
        neon.create_or_merge_neontology_relationship(
            ent_rels.DepartmentManagesSubject(source=department_node, target=subject_node),
            database=db_name, operation='merge'
        )
        logging.info(f"Created subject node for {subject_row['Subject']} and linked to department {subject_row['Department']}")
    
    # Process any additional subjects from year group syllabuses (these won't have department info)
    for _, subject_row in additional_subjects.iterrows():
        subject_unique_id = f"Subject_{school_node.unique_id}_{subject_row['SubjectCode']}"
        # Create in a special "Unassigned" department
        unassigned_dept_name = "Unassigned Department"
        if unassigned_dept_name not in node_library['department_nodes']:
            _, dept_path = fs_handler.create_school_department_directory(school_node.path, unassigned_dept_name)
            department_node = neo_entity.DepartmentNode(
                unique_id=f"Department_{school_node.unique_id}_Unassigned",
                department_name=unassigned_dept_name,
                path=dept_path
            )
            neon.create_or_merge_neontology_node(department_node, database=db_name, operation='merge')
            fs_handler.create_default_tldraw_file(department_node.path, department_node.to_dict())
            node_library['department_nodes'][unassigned_dept_name] = department_node
            
            # Link unassigned department to department structure
            neon.create_or_merge_neontology_relationship(
                ent_rels.DepartmentStructureHasDepartment(source=department_structure_node, target=department_node),
                database=db_name, operation='merge'
            )
            logging.info(f"Created unassigned department node and linked to department structure")
        
        _, subject_path = fs_handler.create_department_subject_directory(
            node_library['department_nodes'][unassigned_dept_name].path, 
            subject_row['Subject']
        )
        
        subject_node = neo_curriculum.SubjectNode(
            unique_id=subject_unique_id,
            subject_code=subject_row['SubjectCode'],
            subject_name=subject_row['Subject'],
            path=subject_path
        )
        # Create subject in both databases
        neon.create_or_merge_neontology_node(subject_node, database=db_name, operation='merge')
        neon.create_or_merge_neontology_node(subject_node, database=curriculum_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(subject_node.path, subject_node.to_dict())
        node_library['subject_nodes'][subject_row['Subject']] = subject_node
        
        # Link subject to unassigned department in school database only
        neon.create_or_merge_neontology_relationship(
            ent_rels.DepartmentManagesSubject(
                source=node_library['department_nodes'][unassigned_dept_name], 
                target=subject_node
            ),
            database=db_name, operation='merge'
        )
        logging.warning(f"Created subject node for {subject_row['Subject']} in unassigned department")
    
    # Process key stages and syllabuses
    logging.info(f"Processing key stages")
    last_key_stage_node = None
    # Track last syllabus nodes per subject
    last_key_stage_syllabus_nodes = {}  # Dictionary to track last key stage syllabus node per subject
    last_year_group_syllabus_nodes = {}  # Dictionary to track last year group syllabus node per subject
    topics_processed = set()  # Track which topics have been processed
    lessons_processed = set()  # Track which lessons have been processed
    statements_processed = set()  # Track which statements have been processed
    
    # First create all key stage nodes and key stage syllabus nodes
    for index, ks_row in keystagesyllabus_df.sort_values('KeyStage').iterrows():
        key_stage = str(ks_row['KeyStage'])
        logging.debug(f"Processing key stage syllabus row - Subject: {ks_row['Subject']}, Key Stage: {key_stage}")
        
        subject_node = node_library['subject_nodes'].get(ks_row['Subject'])
        if not subject_node:
            logging.warning(f"No subject node found for subject {ks_row['Subject']}")
            continue
            
        if key_stage not in key_stage_nodes_created:
            key_stage_node_unique_id = f"KeyStage_{curriculum_node.unique_id}_KStg{key_stage}"
            key_stage_node = neo_curriculum.KeyStageNode(
                unique_id=key_stage_node_unique_id,
                key_stage_name=f"Key Stage {key_stage}",
                key_stage=str(key_stage),
                path=os.path.join(curriculum_node.path, "key_stages", f"KS{key_stage}")
            )
            # Create key stage node in both databases
            neon.create_or_merge_neontology_node(key_stage_node, database=db_name, operation='merge')
            neon.create_or_merge_neontology_node(key_stage_node, database=curriculum_db_name, operation='merge')
            fs_handler.create_default_tldraw_file(key_stage_node.path, key_stage_node.to_dict())
            key_stage_nodes_created[key_stage] = key_stage_node
            node_library['key_stage_nodes'][key_stage] = key_stage_node
            
            # Create relationship with curriculum structure in school database only
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.CurriculumStructureIncludesKeyStage(source=curriculum_node, target=key_stage_node),
                database=db_name, operation='merge'
            )
            logging.info(f"Created key stage node {key_stage_node_unique_id} and relationship with curriculum structure")

            # Create sequential relationship between key stages in both databases
            if last_key_stage_node:
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.KeyStageFollowsKeyStage(source=last_key_stage_node, target=key_stage_node),
                    database=db_name, operation='merge'
                )
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.KeyStageFollowsKeyStage(source=last_key_stage_node, target=key_stage_node),
                    database=curriculum_db_name, operation='merge'
                )
                logging.info(f"Created sequential relationship between key stages {last_key_stage_node.unique_id} and {key_stage_node.unique_id}")
            last_key_stage_node = key_stage_node

        # Create key stage syllabus under the subject's curriculum directory
        _, key_stage_syllabus_path = fs_handler.create_curriculum_key_stage_syllabus_directory(
            curriculum_node.path,
            key_stage,
            ks_row['Subject'],
            ks_row['ID']
        )
        logging.debug(f"Creating key stage syllabus node for {ks_row['Subject']} KS{key_stage} with ID {ks_row['ID']}")
        
        key_stage_syllabus_node_unique_id = f"KeyStageSyllabus_{curriculum_node.unique_id}_{ks_row['Title'].replace(' ', '')}"
        key_stage_syllabus_node = neo_curriculum.KeyStageSyllabusNode(
            unique_id=key_stage_syllabus_node_unique_id,
            ks_syllabus_id=ks_row['ID'],
            ks_syllabus_name=ks_row['Title'],
            ks_syllabus_key_stage=str(ks_row['KeyStage']),
            ks_syllabus_subject=ks_row['Subject'],
            ks_syllabus_subject_code=ks_row['Subject'],
            path=key_stage_syllabus_path
        )
        # Create key stage syllabus node in both databases
        neon.create_or_merge_neontology_node(key_stage_syllabus_node, database=db_name, operation='merge')
        neon.create_or_merge_neontology_node(key_stage_syllabus_node, database=curriculum_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(key_stage_syllabus_node.path, key_stage_syllabus_node.to_dict())
        node_library['key_stage_syllabus_nodes'][ks_row['ID']] = key_stage_syllabus_node
        logging.debug(f"Created key stage syllabus node {key_stage_syllabus_node_unique_id} for {ks_row['Subject']} KS{key_stage}")
        
        # Link key stage syllabus to its subject in both databases
        if subject_node:
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.SubjectHasKeyStageSyllabus(source=subject_node, target=key_stage_syllabus_node),
                database=db_name, operation='merge'
            )
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.SubjectHasKeyStageSyllabus(source=subject_node, target=key_stage_syllabus_node),
                database=curriculum_db_name, operation='merge'
            )
            logging.info(f"Created relationship between subject {subject_node.unique_id} and key stage syllabus {key_stage_syllabus_node.unique_id}")
        
        # Link key stage syllabus to its key stage in both databases
        key_stage_node = key_stage_nodes_created.get(key_stage)
        if key_stage_node:
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.KeyStageIncludesKeyStageSyllabus(source=key_stage_node, target=key_stage_syllabus_node),
                database=db_name, operation='merge'
            )
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.KeyStageIncludesKeyStageSyllabus(source=key_stage_node, target=key_stage_syllabus_node),
                database=curriculum_db_name, operation='merge'
            )
            logging.info(f"Created relationship between key stage {key_stage_node.unique_id} and key stage syllabus {key_stage_syllabus_node.unique_id}")
        
        # Create sequential relationship between key stage syllabuses in both databases
        last_key_stage_syllabus_node = last_key_stage_syllabus_nodes.get(ks_row['Subject'])
        if last_key_stage_syllabus_node:
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.KeyStageSyllabusFollowsKeyStageSyllabus(source=last_key_stage_syllabus_node, target=key_stage_syllabus_node),
                database=db_name, operation='merge'
            )
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.KeyStageSyllabusFollowsKeyStageSyllabus(source=last_key_stage_syllabus_node, target=key_stage_syllabus_node),
                database=curriculum_db_name, operation='merge'
            )
            logging.info(f"Created sequential relationship between key stage syllabuses {last_key_stage_syllabus_node.unique_id} and {key_stage_syllabus_node.unique_id}")
        last_key_stage_syllabus_nodes[ks_row['Subject']] = key_stage_syllabus_node
    
    # Now process year groups and their syllabuses
    for index, ks_row in keystagesyllabus_df.sort_values('KeyStage').iterrows():
        key_stage = str(ks_row['KeyStage'])
        related_yeargroups = sort_year_groups(yeargroupsyllabus_df[yeargroupsyllabus_df['KeyStage'] == ks_row['KeyStage']])
        
        logging.info(f"Processing year groups for key stage {key_stage}")
        for yg_index, yg_row in related_yeargroups.iterrows():
            year_group = yg_row['YearGroup']
            subject_code = yg_row['SubjectCode']
            numeric_year_group = pd.to_numeric(year_group, errors='coerce')

            if pd.notna(numeric_year_group):
                numeric_year_group = int(numeric_year_group)
                if numeric_year_group not in year_group_nodes_created:
                    # Create year group directory under pastoral structure
                    _, year_group_path = fs_handler.create_pastoral_year_group_directory(pastoral_node.path, year_group)
                    logging.info(f"Created year group directory for {year_group_path}")
                    
                    year_group_node_unique_id = f"YearGroup_{school_node.unique_id}_YGrp{numeric_year_group}"
                    year_group_node = neo_curriculum.YearGroupNode(
                        unique_id=year_group_node_unique_id,
                        year_group=str(numeric_year_group),
                        year_group_name=f"Year {numeric_year_group}",
                        path=year_group_path
                    )
                    # Create year group node in both databases but use same directory
                    neon.create_or_merge_neontology_node(year_group_node, database=db_name, operation='merge')
                    neon.create_or_merge_neontology_node(year_group_node, database=curriculum_db_name, operation='merge')
                    fs_handler.create_default_tldraw_file(year_group_node.path, year_group_node.to_dict())
                    
                    # Create sequential relationship between year groups in both databases
                    if last_year_group_node:
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.YearGroupFollowsYearGroup(source=last_year_group_node, target=year_group_node),
                            database=db_name, operation='merge'
                        )
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.YearGroupFollowsYearGroup(source=last_year_group_node, target=year_group_node),
                            database=curriculum_db_name, operation='merge'
                        )
                        logging.info(f"Created sequential relationship between year groups {last_year_group_node.unique_id} and {year_group_node.unique_id} across key stages")
                    last_year_group_node = year_group_node
                    
                    # Create relationship with Pastoral Structure in school database only
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.PastoralStructureIncludesYearGroup(source=pastoral_node, target=year_group_node),
                        database=db_name, operation='merge'
                    )
                    logging.info(f"Created year group node {year_group_node_unique_id} and relationship with pastoral structure")
                    
                    year_group_nodes_created[numeric_year_group] = year_group_node
                    node_library['year_group_nodes'][str(numeric_year_group)] = year_group_node

            # Create year group syllabus nodes in both databases
            year_group_node = year_group_nodes_created.get(numeric_year_group)
            if year_group_node:
                # Create syllabus directory under curriculum structure
                _, year_group_syllabus_path = fs_handler.create_curriculum_year_group_syllabus_directory(
                    curriculum_node.path,
                    yg_row['Subject'],
                    year_group,
                    yg_row['ID']
                )
                logging.info(f"Created year group syllabus directory for {year_group_syllabus_path}")
                
                year_group_syllabus_node_unique_id = f"YearGroupSyllabus_{school_node.unique_id}_{yg_row['ID']}"
                year_group_syllabus_node = neo_curriculum.YearGroupSyllabusNode(
                    unique_id=year_group_syllabus_node_unique_id,
                    yr_syllabus_id=yg_row['ID'],
                    yr_syllabus_name=yg_row['Title'],
                    yr_syllabus_year_group=str(yg_row['YearGroup']),
                    yr_syllabus_subject=yg_row['Subject'],
                    yr_syllabus_subject_code=yg_row['Subject'],
                    path=year_group_syllabus_path
                )
                
                # Create year group syllabus node in both databases but use same directory
                neon.create_or_merge_neontology_node(year_group_syllabus_node, database=db_name, operation='merge')
                neon.create_or_merge_neontology_node(year_group_syllabus_node, database=curriculum_db_name, operation='merge')
                fs_handler.create_default_tldraw_file(year_group_syllabus_node.path, year_group_syllabus_node.to_dict())
                node_library['year_group_syllabus_nodes'][yg_row['ID']] = year_group_syllabus_node
                
                # Create sequential relationship between year group syllabuses in both databases
                last_year_group_syllabus_node = last_year_group_syllabus_nodes.get(yg_row['Subject'])
                # Only create sequential relationship if this year group is higher than the last one
                if last_year_group_syllabus_node:
                    last_year = pd.to_numeric(last_year_group_syllabus_node.yr_syllabus_year_group, errors='coerce')
                    current_year = pd.to_numeric(year_group_syllabus_node.yr_syllabus_year_group, errors='coerce')
                    if pd.notna(last_year) and pd.notna(current_year) and current_year > last_year:
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.YearGroupSyllabusFollowsYearGroupSyllabus(source=last_year_group_syllabus_node, target=year_group_syllabus_node),
                            database=db_name, operation='merge'
                        )
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.YearGroupSyllabusFollowsYearGroupSyllabus(source=last_year_group_syllabus_node, target=year_group_syllabus_node),
                            database=curriculum_db_name, operation='merge'
                        )
                        logging.info(f"Created sequential relationship between year group syllabuses {last_year_group_syllabus_node.unique_id} and {year_group_syllabus_node.unique_id}")
                last_year_group_syllabus_nodes[yg_row['Subject']] = year_group_syllabus_node
                
                # Create relationships in both databases using MATCH to avoid cartesian products
                subject_node = node_library['subject_nodes'].get(yg_row['Subject'])
                if subject_node:
                    # Link to subject
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.SubjectHasYearGroupSyllabus(source=subject_node, target=year_group_syllabus_node),
                        database=db_name, operation='merge'
                    )
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.SubjectHasYearGroupSyllabus(source=subject_node, target=year_group_syllabus_node),
                        database=curriculum_db_name, operation='merge'
                    )
                    logging.info(f"Created relationship between subject {subject_node.unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")
                
                # Link to year group
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.YearGroupHasYearGroupSyllabus(source=year_group_node, target=year_group_syllabus_node),
                    database=db_name, operation='merge'
                )
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.YearGroupHasYearGroupSyllabus(source=year_group_node, target=year_group_syllabus_node),
                    database=curriculum_db_name, operation='merge'
                )
                logging.info(f"Created relationship between year group {year_group_node.unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")
                
                # Link to key stage syllabus if it exists for the same subject
                key_stage_syllabus_node = node_library['key_stage_syllabus_nodes'].get(ks_row['ID'])
                if key_stage_syllabus_node and yg_row['Subject'] == ks_row['Subject']:
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.KeyStageSyllabusIncludesYearGroupSyllabus(source=key_stage_syllabus_node, target=year_group_syllabus_node),
                        database=db_name, operation='merge'
                    )
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.KeyStageSyllabusIncludesYearGroupSyllabus(source=key_stage_syllabus_node, target=year_group_syllabus_node),
                        database=curriculum_db_name, operation='merge'
                    )
                    logging.info(f"Created relationship between key stage syllabus {key_stage_syllabus_node.unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")

                # Process topics for this year group syllabus only if not already processed
                topics_for_syllabus = topic_df[topic_df['SyllabusYearID'] == yg_row['ID']]
                for _, topic_row in topics_for_syllabus.iterrows():
                    if topic_row['TopicID'] in topics_processed:
                        continue
                    topics_processed.add(topic_row['TopicID'])
                    
                    # Get the correct subject from the topic row
                    topic_subject = topic_row['SyllabusSubject']
                    topic_key_stage = topic_row['SyllabusKeyStage']
                    
                    logging.debug(f"Processing topic {topic_row['TopicID']} for subject {topic_subject} and key stage {topic_key_stage}")
                    logging.debug(f"Available key stage syllabus nodes: {[node.ks_syllabus_subject + '_KS' + node.ks_syllabus_key_stage for node in node_library['key_stage_syllabus_nodes'].values()]}")
                    
                    # Find the key stage syllabus node by iterating through all nodes
                    matching_syllabus_node = None
                    for syllabus_node in node_library['key_stage_syllabus_nodes'].values():
                        logging.debug(f"Checking syllabus node - Subject: {syllabus_node.ks_syllabus_subject}, Key Stage: {syllabus_node.ks_syllabus_key_stage}")
                        logging.debug(f"Comparing with - Subject: {topic_subject}, Key Stage: {str(topic_key_stage)}")
                        logging.debug(f"Types - Node Subject: {type(syllabus_node.ks_syllabus_subject)}, Topic Subject: {type(topic_subject)}")
                        logging.debug(f"Types - Node Key Stage: {type(syllabus_node.ks_syllabus_key_stage)}, Topic Key Stage: {type(str(topic_key_stage))}")
                        
                        if (syllabus_node.ks_syllabus_subject == topic_subject and 
                            syllabus_node.ks_syllabus_key_stage == str(topic_key_stage)):
                            matching_syllabus_node = syllabus_node
                            logging.debug(f"Found matching syllabus node: {syllabus_node.unique_id}")
                            break
                    
                    if not matching_syllabus_node:
                        logging.warning(f"No key stage syllabus node found for subject {topic_subject} and key stage {topic_key_stage}, skipping topic creation")
                        continue
                    
                    _, topic_path = fs_handler.create_curriculum_topic_directory(matching_syllabus_node.path, topic_row['TopicID'])
                    logging.info(f"Created topic directory for {topic_path}")
                    
                    topic_node_unique_id = f"Topic_{matching_syllabus_node.unique_id}_{topic_row['TopicID']}"
                    topic_node = neo_curriculum.TopicNode(
                        unique_id=topic_node_unique_id,
                        topic_id=topic_row['TopicID'],
                        topic_title=topic_row.get('TopicTitle', default_topic_values['topic_title']),
                        total_number_of_lessons_for_topic=str(topic_row.get('TotalNumberOfLessonsForTopic', default_topic_values['total_number_of_lessons_for_topic'])),
                        topic_type=topic_row.get('TopicType', default_topic_values['topic_type']),
                        topic_assessment_type=topic_row.get('TopicAssessmentType', default_topic_values['topic_assessment_type']),
                        path=topic_path
                    )
                    # Create topic node in curriculum database only
                    neon.create_or_merge_neontology_node(topic_node, database=curriculum_db_name, operation='merge')
                    fs_handler.create_default_tldraw_file(topic_node.path, topic_node.to_dict())
                    node_library['topic_nodes'][topic_row['TopicID']] = topic_node
                    
                    # Link topic to key stage syllabus as well as year group syllabus
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.KeyStageSyllabusIncludesTopic(source=matching_syllabus_node, target=topic_node),
                        database=curriculum_db_name, operation='merge'
                    )
                    neon.create_or_merge_neontology_relationship(
                        curricular_relationships.YearGroupSyllabusIncludesTopic(source=year_group_syllabus_node, target=topic_node),
                        database=curriculum_db_name, operation='merge'
                    )
                    logging.info(f"Created relationships between topic {topic_node_unique_id} and key stage syllabus {matching_syllabus_node.unique_id} and year group syllabus {year_group_syllabus_node_unique_id}")

                    # Process lessons for this topic only if not already processed
                    lessons_for_topic = lesson_df[
                        (lesson_df['TopicID'] == topic_row['TopicID']) & 
                        (lesson_df['SyllabusSubject'] == topic_subject)
                    ].copy()
                    lessons_for_topic.loc[:, 'Lesson'] = lessons_for_topic['Lesson'].astype(str)
                    lessons_for_topic = lessons_for_topic.sort_values('Lesson')

                    previous_lesson_node = None
                    for _, lesson_row in lessons_for_topic.iterrows():
                        if lesson_row['LessonID'] in lessons_processed:
                            continue
                        lessons_processed.add(lesson_row['LessonID'])
                        
                        _, lesson_path = fs_handler.create_curriculum_lesson_directory(topic_path, lesson_row['LessonID'])
                        logging.info(f"Created lesson directory for {lesson_path}")
                        
                        lesson_data = {
                            'unique_id': f"TopicLesson_{topic_node_unique_id}_{lesson_row['LessonID']}",
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
                                lesson_data[key] = default_topic_lesson_values.get(key, 'Null')

                        lesson_node = neo_curriculum.TopicLessonNode(**lesson_data)
                        # Create lesson node in curriculum database only
                        neon.create_or_merge_neontology_node(lesson_node, database=curriculum_db_name, operation='merge')
                        fs_handler.create_default_tldraw_file(lesson_node.path, lesson_node.to_dict())
                        node_library['topic_lesson_nodes'][lesson_row['LessonID']] = lesson_node
                        
                        # Link lesson to topic
                        neon.create_or_merge_neontology_relationship(
                            curricular_relationships.TopicIncludesTopicLesson(source=topic_node, target=lesson_node),
                            database=curriculum_db_name, operation='merge'
                        )
                        logging.info(f"Created lesson node {lesson_node.unique_id} and relationship with topic {topic_node.unique_id}")

                        # Create sequential relationships between lessons
                        if lesson_row['Lesson'].isdigit() and previous_lesson_node:
                            neon.create_or_merge_neontology_relationship(
                                curricular_relationships.TopicLessonFollowsTopicLesson(source=previous_lesson_node, target=lesson_node),
                                database=curriculum_db_name, operation='merge'
                            )
                            logging.info(f"Created sequential relationship between lessons {previous_lesson_node.unique_id} and {lesson_node.unique_id}")
                        previous_lesson_node = lesson_node

                        # Process learning statements for this lesson only if not already processed
                        statements_for_lesson = statement_df[
                            (statement_df['LessonID'] == lesson_row['LessonID']) & 
                            (statement_df['SyllabusSubject'] == topic_subject)
                        ]
                        for _, statement_row in statements_for_lesson.iterrows():
                            if statement_row['StatementID'] in statements_processed:
                                continue
                            statements_processed.add(statement_row['StatementID'])
                            
                            _, statement_path = fs_handler.create_curriculum_learning_statement_directory(lesson_path, statement_row['StatementID'])
                            
                            statement_data = {
                                'unique_id': f"LearningStatement_{lesson_node.unique_id}_{statement_row['StatementID']}",
                                'lesson_learning_statement_id': statement_row['StatementID'],
                                'lesson_learning_statement': statement_row.get('LearningStatement', default_learning_statement_values['lesson_learning_statement']),
                                'lesson_learning_statement_type': statement_row.get('StatementType', default_learning_statement_values['lesson_learning_statement_type']),
                                'path': statement_path
                            }
                            for key in statement_data:
                                if pd.isna(statement_data[key]):
                                    statement_data[key] = default_learning_statement_values.get(key, 'Null')

                            statement_node = neo_curriculum.LearningStatementNode(**statement_data)
                            # Create statement node in curriculum database only
                            neon.create_or_merge_neontology_node(statement_node, database=curriculum_db_name, operation='merge')
                            fs_handler.create_default_tldraw_file(statement_node.path, statement_node.to_dict())
                            node_library['statement_nodes'][statement_row['StatementID']] = statement_node
                            
                            # Link learning statement to lesson
                            neon.create_or_merge_neontology_relationship(
                                curricular_relationships.LessonIncludesLearningStatement(source=lesson_node, target=statement_node),
                                database=curriculum_db_name, operation='merge'
                            )
                            logging.info(f"Created learning statement node {statement_node.unique_id} and relationship with lesson {lesson_node.unique_id}")
            else:
                logging.warning(f"No year group node found for year group {year_group}, skipping syllabus creation")
    
    # After processing all year groups and their syllabuses, process any remaining topics
    logging.info("Processing topics without year groups")
    for _, topic_row in topic_df.iterrows():
        if topic_row['TopicID'] in topics_processed:
            continue
            
        topic_subject = topic_row['SyllabusSubject']
        topic_key_stage = topic_row['SyllabusKeyStage']
        
        logging.debug(f"Processing topic {topic_row['TopicID']} for subject {topic_subject} and key stage {topic_key_stage} without year group")
        
        # Find the key stage syllabus node
        matching_syllabus_node = None
        for syllabus_node in node_library['key_stage_syllabus_nodes'].values():
            if (syllabus_node.ks_syllabus_subject == topic_subject and 
                syllabus_node.ks_syllabus_key_stage == str(topic_key_stage)):
                matching_syllabus_node = syllabus_node
                break
        
        if not matching_syllabus_node:
            logging.warning(f"No key stage syllabus node found for subject {topic_subject} and key stage {topic_key_stage}, skipping topic creation")
            continue
        
        _, topic_path = fs_handler.create_curriculum_topic_directory(matching_syllabus_node.path, topic_row['TopicID'])
        logging.info(f"Created topic directory for {topic_path}")
        
        topic_node_unique_id = f"Topic_{matching_syllabus_node.unique_id}_{topic_row['TopicID']}"
        topic_node = neo_curriculum.TopicNode(
            unique_id=topic_node_unique_id,
            topic_id=topic_row['TopicID'],
            topic_title=topic_row.get('TopicTitle', default_topic_values['topic_title']),
            total_number_of_lessons_for_topic=str(topic_row.get('TotalNumberOfLessonsForTopic', default_topic_values['total_number_of_lessons_for_topic'])),
            topic_type=topic_row.get('TopicType', default_topic_values['topic_type']),
            topic_assessment_type=topic_row.get('TopicAssessmentType', default_topic_values['topic_assessment_type']),
            path=topic_path
        )
        # Create topic node in curriculum database only
        neon.create_or_merge_neontology_node(topic_node, database=curriculum_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(topic_node.path, topic_node.to_dict())
        node_library['topic_nodes'][topic_row['TopicID']] = topic_node
        topics_processed.add(topic_row['TopicID'])
        
        # Link topic to key stage syllabus
        neon.create_or_merge_neontology_relationship(
            curricular_relationships.KeyStageSyllabusIncludesTopic(source=matching_syllabus_node, target=topic_node),
            database=curriculum_db_name, operation='merge'
        )
        logging.info(f"Created relationship between topic {topic_node_unique_id} and key stage syllabus {matching_syllabus_node.unique_id}")
        
        # Process lessons for this topic
        lessons_for_topic = lesson_df[
            (lesson_df['TopicID'] == topic_row['TopicID']) & 
            (lesson_df['SyllabusSubject'] == topic_subject)
        ].copy()
        lessons_for_topic.loc[:, 'Lesson'] = lessons_for_topic['Lesson'].astype(str)
        lessons_for_topic = lessons_for_topic.sort_values('Lesson')
        
        previous_lesson_node = None
        for _, lesson_row in lessons_for_topic.iterrows():
            if lesson_row['LessonID'] in lessons_processed:
                continue
            lessons_processed.add(lesson_row['LessonID'])
            
            _, lesson_path = fs_handler.create_curriculum_lesson_directory(topic_path, lesson_row['LessonID'])
            logging.info(f"Created lesson directory for {lesson_path}")
            
            lesson_data = {
                'unique_id': f"TopicLesson_{topic_node_unique_id}_{lesson_row['LessonID']}",
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
                    lesson_data[key] = default_topic_lesson_values.get(key, 'Null')
            
            lesson_node = neo_curriculum.TopicLessonNode(**lesson_data)
            # Create lesson node in curriculum database only
            neon.create_or_merge_neontology_node(lesson_node, database=curriculum_db_name, operation='merge')
            fs_handler.create_default_tldraw_file(lesson_node.path, lesson_node.to_dict())
            node_library['topic_lesson_nodes'][lesson_row['LessonID']] = lesson_node
            
            # Link lesson to topic
            neon.create_or_merge_neontology_relationship(
                curricular_relationships.TopicIncludesTopicLesson(source=topic_node, target=lesson_node),
                database=curriculum_db_name, operation='merge'
            )
            logging.info(f"Created lesson node {lesson_node.unique_id} and relationship with topic {topic_node.unique_id}")
            
            # Create sequential relationships between lessons
            if lesson_row['Lesson'].isdigit() and previous_lesson_node:
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.TopicLessonFollowsTopicLesson(source=previous_lesson_node, target=lesson_node),
                    database=curriculum_db_name, operation='merge'
                )
                logging.info(f"Created sequential relationship between lessons {previous_lesson_node.unique_id} and {lesson_node.unique_id}")
            previous_lesson_node = lesson_node
            
            # Process learning statements for this lesson
            statements_for_lesson = statement_df[
                (statement_df['LessonID'] == lesson_row['LessonID']) & 
                (statement_df['SyllabusSubject'] == topic_subject)
            ]
            for _, statement_row in statements_for_lesson.iterrows():
                if statement_row['StatementID'] in statements_processed:
                    continue
                statements_processed.add(statement_row['StatementID'])
                
                _, statement_path = fs_handler.create_curriculum_learning_statement_directory(lesson_path, statement_row['StatementID'])
                
                statement_data = {
                    'unique_id': f"LearningStatement_{lesson_node.unique_id}_{statement_row['StatementID']}",
                    'lesson_learning_statement_id': statement_row['StatementID'],
                    'lesson_learning_statement': statement_row.get('LearningStatement', default_learning_statement_values['lesson_learning_statement']),
                    'lesson_learning_statement_type': statement_row.get('StatementType', default_learning_statement_values['lesson_learning_statement_type']),
                    'path': statement_path
                }
                for key in statement_data:
                    if pd.isna(statement_data[key]):
                        statement_data[key] = default_learning_statement_values.get(key, 'Null')
                
                statement_node = neo_curriculum.LearningStatementNode(**statement_data)
                # Create statement node in curriculum database only
                neon.create_or_merge_neontology_node(statement_node, database=curriculum_db_name, operation='merge')
                fs_handler.create_default_tldraw_file(statement_node.path, statement_node.to_dict())
                node_library['statement_nodes'][statement_row['StatementID']] = statement_node
                
                # Link learning statement to lesson
                neon.create_or_merge_neontology_relationship(
                    curricular_relationships.LessonIncludesLearningStatement(source=lesson_node, target=statement_node),
                    database=curriculum_db_name, operation='merge'
                )
                logging.info(f"Created learning statement node {statement_node.unique_id} and relationship with lesson {lesson_node.unique_id}")
    
    return node_library