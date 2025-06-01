import uuid
import time
import os
import hashlib
import logging

# Dictionary to store session tokens
# Format: {connection_uuid: {"token": token_string, "expiry": timestamp}}
active_tokens = {}

def verify_password(password):
    """
    Verify if the provided password matches the secret key.
    
    Args:
        password (str): Password to verify
    
    Returns:
        bool: True if password matches, False otherwise
    """
    # Get the secret key from environment variable
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        logging.warning("SECRET_KEY environment variable not set")
        return False
        
    # Simple comparison for now (consider using secure comparison in production)
    return password == secret_key

def generate_token():
    """
    Generate a unique session token.
    
    Returns:
        str: Unique session token
    """
    # Generate a random UUID and hash it for additional security
    token = str(uuid.uuid4())
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    return hashed_token

def save_token(connection_uuid, token, expiry_seconds=86400):
    """
    Save a token for a specific connection UUID.
    
    Args:
        connection_uuid (str): Connection UUID
        token (str): Session token
        expiry_seconds (int, optional): Token expiry time in seconds. Defaults to 86400 (24 hours).
    """
    expiry_time = time.time() + expiry_seconds
    active_tokens[connection_uuid] = {"token": token, "expiry": expiry_time}
    
def get_stored_token(connection_uuid):
    """
    Get the stored token for a specific connection UUID.
    
    Args:
        connection_uuid (str): Connection UUID
    
    Returns:
        str or None: Stored token if exists and not expired, None otherwise
    """
    token_data = active_tokens.get(connection_uuid)
    if not token_data:
        return None
        
    # Check if token has expired
    if token_data["expiry"] < time.time():
        # Token expired, remove it
        del active_tokens[connection_uuid]
        return None
        
    return token_data["token"]

def verify_token(token):
    """
    Verify if a token is valid and not expired.
    
    Args:
        token (str): Token to verify
    
    Returns:
        bool: True if token is valid and not expired, False otherwise
    """
    if not token:
        return False
        
    current_time = time.time()
    
    # Check if token exists in any connection
    for connection_uuid, token_data in active_tokens.items():
        if token_data["token"] == token:
            # Check if token has expired
            if token_data["expiry"] < current_time:
                # Token expired, remove it
                del active_tokens[connection_uuid]
                return False
            return True
            
    return False

def is_token_valid(connection_uuid):
    """
    Check if a valid token exists for the given connection UUID.
    
    Args:
        connection_uuid (str): Connection UUID
    
    Returns:
        bool: True if a valid token exists, False otherwise
    """
    token = get_stored_token(connection_uuid)
    return token is not None

def remove_token(connection_uuid):
    """
    Remove a token for a specific connection UUID.
    
    Args:
        connection_uuid (str): Connection UUID
    
    Returns:
        bool: True if token was removed, False if it didn't exist
    """
    if connection_uuid in active_tokens:
        del active_tokens[connection_uuid]
        return True
    return False

def cleanup_expired_tokens():
    """
    Clean up all expired tokens.
    
    Returns:
        int: Number of tokens removed
    """
    current_time = time.time()
    expired_connections = [
        connection_uuid 
        for connection_uuid, token_data in active_tokens.items() 
        if token_data["expiry"] < current_time
    ]
    
    for connection_uuid in expired_connections:
        del active_tokens[connection_uuid]
        
    return len(expired_connections) 