def format_user_email_for_neo_db(user_email):
    """Format user email for Neo4j database name.
    
    Neo4j database names can only contain letters, numbers, dots, and dashes.
    We'll convert the email to a valid format:
    example@domain.com -> ccuser-example-at-domain-com
    
    Args:
        user_email: Email address to format
        
    Returns:
        Formatted string suitable for Neo4j database name
    """
    # Convert to lowercase and replace special characters
    sanitized = user_email.lower()
    sanitized = sanitized.replace('@', 'at')
    sanitized = sanitized.replace('.', 'dot')
    sanitized = sanitized.replace('_', 'underscore')
    sanitized = sanitized.replace('-', 'dash')

    return f"{sanitized}"