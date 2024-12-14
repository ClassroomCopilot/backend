from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_neo4j_session_tools'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import modules.database.tools.queries as query
from contextlib import suppress

def get_node_by_unique_id_and_adjacent_nodes(session, unique_id):
    return session.read_transaction(_get_node_by_unique_id_and_adjacent_nodes, unique_id)

def _get_node_by_unique_id_and_adjacent_nodes(tx, unique_id):
    query = """
    MATCH (n {unique_id: $unique_id})
    OPTIONAL MATCH (n)-[r]-(adjacent)
    RETURN n AS node, COLLECT(DISTINCT {node: adjacent, relationship: r}) AS connected_nodes
    """
    result = tx.run(query, unique_id=unique_id)
    record = result.single()
    if record:
        node = record["node"]
        connected_nodes = record["connected_nodes"]
        return {"node": node, "connected_nodes": connected_nodes}
    return None

def delete_all_nodes_and_relationships(session):
    total_deleted = 0
    while True:
        deleted_count = session.write_transaction(_delete_batch)
        total_deleted += deleted_count
        if deleted_count == 0:
            break

def _delete_batch(tx):
    result_data = tx.run(query.delete_batch, batch_size=10000).single()
    return 0 if result_data is None else result_data[0]

def delete_all_constraints(session):
    if show_constraints_result := session.run(query.show_constraints).data():
        for constraint in show_constraints_result:
            constraint_name = constraint['name']
            session.run(query.drop_constraint(constraint_name))
        
def reset_all_indexes(session):
    indexes = session.run(query.show_indexes).data()
    for index in indexes:
        index_name = index['name']
        session.run(query.drop_index(index_name))
        
def reset_databases(session):
    delete_all_nodes_and_relationships(session)
    delete_all_constraints(session)
    reset_all_indexes(session)
    
def close_session(session):
    if session:
        with suppress(Exception):
            session.close()

def create_node(session, label, properties, returns=False):
    """
    Function to create a node in Neo4j database.
    
    Args:
        driver (neo4j.Driver): The Neo4j driver.
        session (str): The Neo4j session.
        label (str): The label of the node.
        properties (dict): A dictionary of properties for the node.
        
    Example usage:
        create_node(neo4j_driver, "Topic", {"TopicID": "AP.PAG10", "Title": "Topic 10"})
        
    Returns:
        None
    """
    transaction = session.write_transaction(_create_node, label, properties)
    if returns:
        transaction_id = transaction.id
        # logging.database(f"Created {label} node with transaction ID {transaction_id} and properties {properties}")
        print(f"Created {label} node with transaction ID {transaction_id} and properties {properties}")
        return find_node_by_transaction_id(session, transaction_id)
    else:
        # logging.warning(f"Failed to create {label} node with properties {properties}")
        print(f"Failed to create {label} node with properties {properties}")
        return None

def _create_node(tx, label, properties):
    query = f"""
    CREATE (n:{label} $properties)
    RETURN n
    """
    # logging.query(f"Running query: {query}")
    print(f"Running query: {query}")
    result = tx.run(query, properties=properties)
    return result.single()[0] if result.single() is not None else None  # Handle no record found

# Function to find a node by its element ID
def find_node_by_transaction_id(session, transaction_id):
    """
    Function to find a node in Neo4j database by its element ID.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        element_id (str): The element ID of the node to find.

    Returns:
        The matched node.
    """
    return session.read_transaction(_find_node_by_element_id, transaction_id)
    
def _find_node_by_element_id(tx, transaction_id):
    query = """
    MATCH (n)
    WHERE id(n) = $transaction_id
    RETURN n
    """
    # logging.query(f"Running query: {query}")
    result = tx.run(query, transaction_id=transaction_id)
    record = result.single()  # Get the single result record, if any
    return record[0] if record is not None else None  # Handle no record found

# Function to create a relationship between two nodes in Neo4j
def create_relationship(session, start_node, end_node, label, properties=None, returns=False):
    """
    Function to create a relationship between two nodes in Neo4j database.
    
    Args:
        driver (neo4j.Driver): The Neo4j driver.
        session (str): The Neo4j session.
        start_node (str): The ID of the start node.
        end_node (str): The ID of the end node.
        rel_type (str): The type of the relationship.
        properties (dict): A dictionary of properties for the relationship.
        
    Example usage:
        create_relationship(neo4j_driver, "AP.PAG10", "AP.PAG11", "HAS_NEXT")
        
    Returns:
        None
    """
    relationship = session.write_transaction(_create_relationship, start_node, end_node, label, properties)
    if returns:
        relationship_id = relationship.id
        return find_relationship_by_relationship_id(session, relationship_id)
    else:
        return None
        
def _create_relationship(tx, start_node, end_node, label, properties):
    query = f"""
    MATCH (a), (b)
    WHERE ID(a) = $start_node_id AND ID(b) = $end_node_id
    CREATE (a)-[r:{label}]->(b)
    RETURN r
    """
    # logging.query(f"Running query: {query}")
    result = tx.run(query, start_node_id=start_node.id, end_node_id=end_node.id, properties=properties)
    single_result = result.single()
    return single_result[0] if single_result is not None else None

def order_list_of_nodes_by_property(session, label, property_name, order="ASC"):
    """
    Function to order a list of nodes in Neo4j database by a property.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        label (str): The label of the nodes to find.
        property_name (str): The name of the property to order by.
        order (str): The order of the sorting (ASC or DESC).

    Returns:
        List of matched nodes.
    """
    return session.read_transaction(_order_list_of_nodes_by_property, label, property_name, order)

def _order_list_of_nodes_by_property(tx, label, property_name, order):
    query = f"""
    MATCH (n:{label})
    RETURN n
    ORDER BY n.{property_name} {order}
    """
    # logging.query(f"Running query: {query}")
    result = tx.run(query)
    return [record["n"] for record in result]

def find_relationship_by_relationship_id(session, relationship_id):
    """
    Function to find a relationship in Neo4j database by its relationship ID.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        relationship_id (str): The relationship ID of the relationship to find.

    Returns:
        The matched relationship.
    """
    return session.read_transaction(_find_relationship_by_relationship_id, relationship_id)
    
def _find_relationship_by_relationship_id(tx, relationship_id):
    query = """
    MATCH ()-[r]->()
    WHERE id(r) = $relationship_id
    """
    # logging.query(f"Running query: {query}")
    print(f"Running query: {query}")
    result = tx.run(query, relationship_id=relationship_id)
    record = result.single()  # Get the single result record, if any
    return record[0] if record is not None else None  # Handle no record found

# Function to find nodes in Neo4j database by label
def find_nodes_by_label(session, label):
    """
    Function to find nodes in Neo4j database by label.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        label (str): The label of the nodes to find.
        
    Example usage:
        find_nodes_by_label(neo4j_driver, "Topic")

    Returns:
        List of matched nodes.
    """
    return session.read_transaction(_find_nodes_by_label, label)

def _find_nodes_by_label(tx, label):
    query = f"""
    MATCH (n:{label})
    RETURN n
    """
    # logging.query(f"Running query: {query}")
    print(f"Running query: {query}")
    result = tx.run(query)
    return [record["n"] for record in result]

def get_node_by_unique_id(session, unique_id):
    return session.read_transaction(_get_node_by_unique_id, unique_id)

def _get_node_by_unique_id(tx, unique_id):
    query = f"""
    MATCH (n)
    WHERE n.unique_id = $unique_id
    RETURN n
    """
    logging.debug(f"Executing query with unique_id: {unique_id}")
    result = tx.run(query, unique_id=unique_id)
    record = result.single()
    if record is None:
        logging.warning(f"No node found with unique_id: {unique_id}")
        return None
    return record[0]

# Function to find nodes in Neo4j database by label and properties
def find_nodes_by_label_and_properties(session, label, properties):
    """
    Function to find nodes in Neo4j database by label and properties.

    Args:
        session (neo4j.Session): The Neo4j session.
        label (str): The label of the nodes to find.
        properties (dict): A dictionary of properties to match.

    Returns:
        List of matched nodes.
    """
    logging.debug(f"Finding nodes with label: {label} and properties: {properties}")
    with session:
        response = session.read_transaction(_find_nodes_by_label_and_properties, label, properties)
        logging.debug(f"Response: {response}")
        return response

def _find_nodes_by_label_and_properties(tx, label, properties):
    query = f"""
    MATCH (n:{label})
    WHERE {' AND '.join([f'n.{key} = ${key}' for key in properties.keys()])}
    RETURN n
    """
    logging.debug(f"Running query: {query}")
    result = tx.run(query, **properties)
    logging.debug(f"Result: {result}")
    return [record["n"] for record in result]

# Function to find relationships in Neo4j database by type
def find_relationships_by_type(session, rel_type):
    """
    Function to find relationships in Neo4j database by type.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        rel_type (str): The type of the relationships to find.

    Returns:
        List of matched relationships.
    """
    return session.read_transaction(_find_relationships_by_type, rel_type)
    
def _find_relationships_by_type(tx, rel_type):
    query = f"""
    MATCH ()-[r:{rel_type}]->()
    RETURN r
    """
    # logging.query(f"Running query: {query}")
    print(f"Running query: {query}")
    result = tx.run(query)
    return [record["r"] for record in result]

# Function to find relationships in Neo4j database by type and properties
def find_relationships_by_type_and_properties(session, label, properties):
    """
    Function to find relationships in Neo4j database by type and properties.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        rel_type (str): The type of the relationships to find.
        properties (dict): A dictionary of properties to match.

    Returns:
        List of matched relationships.
    """
    return session.read_transaction(_find_relationships_by_type_and_properties, label, properties)
    

def _find_relationships_by_type_and_properties(tx, label, properties):
    query = f"""
    MATCH (a)-[r:{label}]->(b)
    WHERE {' AND '.join([f'r.{key} = ${key}' for key in properties.keys()])}
    RETURN r
    """
    # logging.query(f"Running query: {query}")
    print(f"Running query: {query}")
    result = tx.run(query, **properties)
    return [record["r"] for record in result]

# Function to find nodes and relationships in Neo4j database by label and properties
def find_nodes_and_relationships_by_label_and_properties(session, label, properties):
    """
    Function to find nodes and relationships in Neo4j database by label and properties.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        label (str): The label of the nodes to find.
        properties (dict): A dictionary of properties to match.

    Returns:
        List of matched nodes and relationships.
    """
    return session.read_transaction(_find_nodes_and_relationships_by_label_and_properties, label, properties)
    
def _find_nodes_and_relationships_by_label_and_properties(tx, label, properties):
    query = f"""
    MATCH (n:{label})
    WHERE {' AND '.join([f'n.{key} = ${key}' for key in properties.keys()])}
    RETURN n
    """
    # logging.query(f"Running query: {query}")
    result = tx.run(query, **properties)
    return [record["n"] for record in result]

# Function to delete nodes in Neo4j based on given criteria
def delete_nodes(session, criteria, delete_related=False):
    """
    Function to delete nodes in Neo4j based on given criteria.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        criteria (dict): A dictionary containing the properties to match for deletion.
        delete_related (bool): If True, deletes related nodes and relationships; otherwise, deletes only the matched nodes.

    Example usage:
        # Delete only the nodes matching the criteria
        delete_nodes(neo4j_driver, {'TopicID': 'AP.PAG10'})

        # Delete the nodes and their related relationships
        delete_nodes(neo4j_driver, {'TopicID': 'AP.PAG10'}, delete_related=True)
    """
    session.write_transaction(_delete_nodes, criteria, delete_related)

def _delete_nodes(tx, criteria, delete_related=False):
    """
    Internal function to execute a Cypher query to delete nodes based on criteria.

    Args:
        tx (neo4j.Transaction): The Neo4j transaction.
        criteria (dict): A dictionary containing the properties to match for deletion.
        delete_related (bool): Specifies whether to delete related nodes and relationships.
    """
    condition_str = " AND ".join([f"n.{key} = ${key}" for key in criteria])
    if delete_related:
        query = f"""
        MATCH (n)-[r]-()
        WHERE {condition_str}
        DELETE n, r
        """
    else:
        query = f"""
        MATCH (n)
        WHERE {condition_str}
        DELETE n
        """
    # logging.query(f"Running query: {query}")
    tx.run(query, **criteria)

# Function to delete all nodes and relationships in the Neo4j database in batches
def delete_lots_of_nodes_and_relationships(session):
    """
    Function to delete all nodes and relationships in the Neo4j database in batches.

    Args:
        driver (neo4j.Driver): The Neo4j driver.
        session (str): The Neo4j session.
    """
    total_deleted = 0
    while True:
        deleted_count = session.write_transaction(_delete_batch)
        total_deleted += deleted_count
        if deleted_count == 0:
            break  # Exit the loop if no more nodes are deleted
    # logging.prod(f"All nodes and relationships have been deleted. Total deleted: {total_deleted}")
    print(f"Neo4j:  All nodes and relationships have been deleted. Total deleted: {total_deleted}")

def _delete_batch(tx):
    """
    Function to execute a Cypher query to delete a batch of nodes and relationships.

    Args:
        tx (neo4j.Transaction): The Neo4j transaction.
    """
    batch_size = 10000  # Adjust the batch size according to your needs
    query = """
    MATCH (n)
    WITH n LIMIT $batch_size
    DETACH DELETE n
    RETURN count(*)
    """
    # logging.query(f"Running query: {query}")
    result = tx.run(query, batch_size=batch_size)
    result_data = result.single()
    
    if result_data is None:
        return 0
    deleted_count = result_data[0]
    if deleted_count is None:  # This check might be redundant, but kept for clarity
        return 0
    if deleted_count > 0:
        # logging.database(f"Deleted {deleted_count} nodes.")
        print(f"Neo4j: Deleted {deleted_count} nodes.")
    return deleted_count

def delete_all_constraints(session):
    # Correct command to fetch all constraints for Neo4j 4.x and later
    constraints_query = "SHOW CONSTRAINTS"
    # logging.query(f"Running query: {constraints_query}")
    if constraints_query_result := session.run(constraints_query).data():
        for constraint in constraints_query_result:
            # Ensure correct key is used to extract constraint name
            constraint_name = constraint['name']  # Adjust this if necessary
            drop_query = f"DROP CONSTRAINT {constraint_name}"
            # logging.query(f"Running query: {drop_query}")
            session.run(drop_query)
            # logging.database(f"Dropped constraint: {constraint_name}")
            print(f"Neo4j: Dropped constraint: {constraint_name}")
    else:
        # logging.warning("No constraints found to delete.")
        print("Neo4j: No constraints found to delete.")
        
def reset_all_indexes(session):
    indexes = session.run("SHOW INDEXES").data()
    for index in indexes:
        index_name = index['name']
        session.run(f"DROP INDEX {index_name}")
        # logging.info(f"Deleted index: {index_name}")
        print(f"Neo4j: Deleted index: {index_name}")

def reset_database_in_session(session):
    logging.debug("Neo4j: Resetting database")
    delete_lots_of_nodes_and_relationships(session)
    delete_all_constraints(session)
    reset_all_indexes(session)
    logging.info("Neo4j: Database reset")

def create_database(session, db_name):
    """
    Creates a new database in Neo4j if it does not already exist.

    Args:
        session (neo4j.Session): The Neo4j session.
        db_name (str): The name of the database to create.
    """
    logging.debug(f"Neo4j: Creating database {db_name}")
    query = f"CREATE DATABASE `{db_name}` IF NOT EXISTS"
    try:
        session.run(query)
        logging.info(f"Neo4j: Database {db_name} created successfully.")
    except Exception as e:
        logging.error(f"Neo4j: Failed to create database {db_name}: {str(e)}")
