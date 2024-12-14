from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_langchain_graph_qa'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter, HTTPException
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts.prompt import PromptTemplate
from routers.llm.private.ollama.ollama_wrapper import OllamaWrapper

router = APIRouter()

# Define the schema for nodes and relationships
node_types = {
    "KeyStage": ["merged", "key_stage_name", "unique_id", "created"],
    "KeyStageSyllabus": ["ks_syllabus_name", "unique_id", "created", "merged", "ks_syllabus_key_stage", "ks_syllabus_subject"],
    "YearGroup": ["created", "merged", "unique_id", "year_group_name"],
    "YearGroupSyllabus": ["created", "merged", "yr_syllabus_name", "yr_syllabus_year_group", "yr_syllabus_id", "yr_syllabus_subject"],
    "Topic": ["topic_type", "topic_assessment_type", "created", "merged", "unique_id", "topic_id", "total_number_of_lessons_for_topic", "topic_title"],
    "Lesson": ["topic_lesson_id", "topic_lesson_type", "created", "merged", "topic_lesson_title", "topic_lesson_length", "topic_lesson_suggested_activities", "topic_lesson_weblinks", "topic_lesson_skills_learned"],
    "LearningStatement": ["created", "merged", "lesson_learning_statement", "lesson_learning_statement_id", "lesson_learning_statement_type"]
}

relationship_types = {
    "KEY_STAGE_INCLUDES_KEY_STAGE_SYLLABUS": ["created", "merged"],
    "KEY_STAGE_SYLLABUS_INCLUDES_YEAR_GROUP_SYLLABUS": ["created", "merged"],
    "YEAR_GROUP_FOLLOWS_YEAR_GROUP": ["created", "merged"],
    "KEY_STAGE_FOLLOWS_KEY_STAGE": ["created", "merged"],
    "YEAR_SYLLABUS_INCLUDES_TOPIC": ["created", "merged"],
    "TOPIC_INCLUDES_LESSON": ["created", "merged"],
    "LESSON_INCLUDES_LEARNING_STATEMENT": ["created", "merged"],
    "LESSON_FOLLOWS_LESSON": ["created", "merged"]
}

@router.get("/prompt")
async def query_graph(
    database: str, prompt: str, top_k: int = 30, model: str = "gpt-4o", temperature: float = 0,
    verbose: bool = False, return_intermediate_steps: bool = False, exclude_types: list = None, include_types: list = None,
    return_direct: bool = False, validate_cypher: bool = False, model_type: str = "openai"
):
    logging.info(f"Received request with prompt: {prompt}")
    if exclude_types is None:
        logging.info("No exclude_types provided, using default.")
        exclude_types = []
    if include_types is None:
        logging.info("No include_types provided, using default.")
        include_types = []

    # Validate include_types and exclude_types
    logging.info(f"Validating include_types and exclude_types...")
    valid_types = set(node_types.keys()).union(set(relationship_types.keys()))
    logging.info(f"Valid types: {valid_types}")
    exclude_types = [t for t in exclude_types if t in valid_types]
    logging.info(f"Validated exclude_types: {exclude_types}")
    include_types = [t for t in include_types if t in valid_types]
    logging.info(f"Validated include_types: {include_types}")

    graph = Neo4jGraph(
        url=f"bolt://{os.environ['HOST_NEO4J']}:{os.environ['NEO4J_BOLT_PORT']}",
        username=os.environ['NEO4J_USER'],
        password=os.environ['NEO4J_PASSWORD'],
        database=database
    )

    logging.info("Refreshing schema...")
    graph.refresh_schema()
    logging.info("Schema refreshed.")
    schema = graph.schema
    logging.info(f"Schema: {schema}")

    CYPHER_GENERATION_TEMPLATE = """Task: Generate a Cypher statement to query a graph database for timetable information.
    Role:
    You are an assistant in a school for teachers, specializing in querying graph databases to find answers to questions.
    The teacher will ask you questions about their timetable.

    Instructions:
    1. Use only the provided relationship types and properties in the schema.
    2. Do not use any other relationship types or properties that are not provided.

    Schema:
    {schema}

    Note:
    1. Do not include any explanations or apologies in your responses.
    2. Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    3. Do not include any text except the generated Cypher statement.

    The question is:
    {question}"""

    CYPHER_GENERATION_PROMPT = PromptTemplate(
        input_variables=["schema", "question"],
        template=CYPHER_GENERATION_TEMPLATE
    )

    if model_type == "ollama":
        ollama_host = os.getenv("OLLAMA_URL")
        ollama_port = os.getenv("OLLAMA_PORT")
        if not ollama_host or not ollama_port:
            raise HTTPException(status_code=500, detail="Ollama host or port not set")
        client = OllamaWrapper(host=f'http://{ollama_host}:{ollama_port}')
        cypher_llm = client
        qa_llm = client
    else:
        cypher_llm = ChatOpenAI(temperature=temperature, model=model)
        qa_llm = ChatOpenAI(temperature=temperature, model=model)

    chain = GraphCypherQAChain.from_llm(
        graph=graph,
        cypher_llm=cypher_llm,
        qa_llm=qa_llm,
        top_k=top_k,
        verbose=verbose,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        return_intermediate_steps=return_intermediate_steps,
        exclude_types=exclude_types,
        include_types=include_types,
        return_direct=return_direct,
        validate_cypher=validate_cypher
    )
    
    formatted_prompt = CYPHER_GENERATION_PROMPT.format(schema=schema, question=prompt)

    logging.info("\n\n")

    logging.info("==================================================")
    logging.info("=            graph_qa.py                         =")
    logging.info("==================================================")
    logging.info(f"Prompt: {prompt}")
    logging.info("--------------------------------------------------")
    logging.info(f"Schema: \n{schema}\n")
    logging.info("--------------------------------------------------")
    logging.info(f"Formatted Prompt: \n{formatted_prompt}\n")
    logging.info("--------------------------------------------------")
    logging.info(f"Cypher prompt: \n{CYPHER_GENERATION_PROMPT}\n")
    logging.info("--------------------------------------------------")
    logging.info(f"Cypher template: \n{CYPHER_GENERATION_TEMPLATE}\n")
    logging.info("--------------------------------------------------")
    logging.info(f"Cypher chain: \n{chain}\n")
    logging.info("==================================================")

    return chain(prompt)