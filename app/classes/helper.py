import base64
import csv
import logging
import os
import random

from flask import current_app, json, session, url_for
import urllib
from app.db import db
from app.models import State_UT, District, Block, ActivityLog, User

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

from app.models.visit_count import VisitCount

    
def create_db(app):
    directory_path = os.path.dirname(__file__).split("/classes")[0]
    with app.app_context():
        # Create tables if not exist
        db.create_all()

        # Populate States
        if State_UT.query.count() == 0:
            states_file = os.path.join(directory_path, 'static/masters', 'state.csv')
            if os.path.exists(states_file):
                with open(states_file, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        state = State_UT(
                            name=row["state_name"],
                            short_name=row.get("short_name"),
                            nrega_id=row.get("state_id"),
                        )
                        db.session.add(state)
                db.session.commit()

        # Populate Districts
        if District.query.count() == 0:
            districts_file = os.path.join(directory_path, "static/masters", "district.csv")
            if os.path.exists(districts_file):
                with open(districts_file, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # normalize names to lowercase for matching
                        state_nrega_id_csv = row["state_id"].strip()

                        state = State_UT.query.filter(
                            db.func.lower(State_UT.nrega_id) == state_nrega_id_csv
                        ).first()

                        if state:
                            district = District(
                                name=row["district_name"].strip(),  # keep original case for saving
                                short_name=row.get("short_name"),
                                nrega_id=row.get("district_id"),
                                state_id=state.id,
                            )
                            db.session.add(district)
                        else:
                            print(f"Skipping district '{row['district_name']}' - state '{row['state_id']}' not found in DB.")
                db.session.commit()

        # Populate Blocks
        if Block.query.count() == 0:
            blocks_file = os.path.join(directory_path, "static/masters", "block.csv")
            if os.path.exists(blocks_file):
                with open(blocks_file, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # normalize names to lowercase for matching
                        district_nrega_id_csv = row["district_id"].strip()

                        district = District.query.filter(
                            db.func.lower(District.nrega_id) == district_nrega_id_csv
                        ).first()

                        if district:
                            block = Block(
                                name=row["block_name"].strip(),  # keep original case for saving
                                short_name=row.get("short_name"),
                                nrega_id=row.get("block_id"),
                                state_id=district.state_id,
                                district_id = district.id
                            )
                            db.session.add(block)
                        else:
                            print(f"Skipping block '{row['block_name']}' - district '{row['district_id']}' not found in DB.")
                db.session.commit()
        
        return True
    

def generate_rsa_key_pair():
    key = RSA.generate(2048)
    public_key_pem = key.publickey().export_key().decode('utf-8')
    private_key_pem = key.export_key().decode('utf-8')
    return public_key_pem, private_key_pem


def decrypt_password(encrypted_password):
    try:
        private_key_pem = current_app.config.get('PRIVATE_KEY')
        if not private_key_pem:
            # error_logger.error("Private key not found in session.")
            return {'error': 'Private key missing for decryption'}

        private_key = RSA.import_key(private_key_pem)
        cipher_rsa = PKCS1_v1_5.new(private_key)

        encrypted_bytes = base64.b64decode(encrypted_password)
        # Sentinel is required for PKCS1_v1_5
        from Crypto.Random import get_random_bytes
        sentinel = get_random_bytes(15)            
        decrypted_bytes = cipher_rsa.decrypt(encrypted_bytes, sentinel)

        if decrypted_bytes == sentinel:
            # error_logger.error("RSA decryption failed (likely wrong key or corrupted ciphertext)")
            return {'error': 'Private key missing for decryption'}
        try:
            cleartext_password = decrypted_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # error_logger.error('Decrypted bytes could not be decoded as UTF-8')
            return {'error': 'Password decode failed'}

        return cleartext_password
    
    except Exception as e:
        # error_logger.error(f"RSA Decryption failed: {str(e)}")
        return {'error': 'Password Decryption failed'}
    
# Generate a math question and store answer

def generate_math_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    operators = [('+', lambda x, y: x + y), ('-', lambda x, y: x - y)]
    op_symbol, op_func = random.choice(operators)

    # Ensure subtraction always results in a positive number
    if op_symbol == '-' and a < b:
        a, b = b, a

    question = f"{a} {op_symbol} {b}"
    answer = op_func(a, b)
    session['captcha_answer'] = str(answer)
    return question


def format_slxapi_query_string(actor: dict, endpoint: str, auth: str) -> str:
    """
    Build the slxapi query string:
    slxapi=<urlencoded JSON>
    """
    payload = {
        "actor": actor,
        "endpoint": endpoint,
        "auth": auth
    }

    json_str = json.dumps(payload, separators=(",", ":"))  # compact JSON
    encoded_str = urllib.parse.quote(json_str, safe="")   # full URL-encoding

    return f"slxapi={encoded_str}"

    # query_parts = []
    # if endpoint:
    #     query_parts.append(f"xapi_endpoint={endpoint}")
    # if auth:
    #     query_parts.append(f"xapi_auth={auth}")
    # if actor:
    #     query_parts.append(f"xapi_actor={actor}")
    # return "&".join(query_parts)

@staticmethod    
def get_basic_auth(key, secret_key):
    """
    Generates a Base64 encoded string for Basic Authentication.

    Args:
        key (str): The username or API key.
        secret_key (str): The password or secret key.

    Returns:
        JSON: A JSON object containing the generated Basic Auth string.
    """
    # Combine the key and secret_key with a colon
    credential_string = f"{key}:{secret_key}"

    # Encode the string to bytes
    credential_bytes = credential_string.encode('utf-8')

    # Base64 encode the bytes
    encoded_bytes = base64.b64encode(credential_bytes)

    # Decode the Base64 bytes to a string
    encoded_string = encoded_bytes.decode('utf-8')

    # Prepend "Basic " to the encoded string as per the Basic Auth standard
    basic_auth_string = f"Basic {encoded_string}"

    return basic_auth_string

def get_lrs_query_string(learner, base_url):
    """
    Takes a JSON payload, modifies it as required, and generates a URL-encoded
    query parameter string for a story.html page.
    """
    try:
        # Get the JSON data from the request body
        # data = request.json
        # if not data:
        #     return jsonify({"error": "Invalid JSON payload"}), 400

        # Create the correct JSON structure for the 'slxapi' parameter
        # Note: The 'endpoint' key in the output is a string, not an object.
        
        basic_auth = get_basic_auth(learner.email, current_app.secret_key)
        correct_payload = {
            "actor":  {
                "mbox": f"mailto:{learner.email}",
                "objectType": "Agent",
                "name": learner.name
                },
            "endpoint": f"{base_url}/api/lrs",
            "auth": basic_auth
        }

        # Convert the Python dictionary to a JSON string
        json_string = json.dumps(correct_payload)

        # URL-encode the JSON string
        encoded_string = urllib.parse.quote(json_string, safe='')

        # Construct the final URL
        return f"slxapi={encoded_string}"

        # return jsonify({"url": final_url})

    except Exception as e:
        return None
    
def setup_logger(name, log_level=logging.INFO):
    """
    Set up professional logging with rotation to prevent disk space issues
    """
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation (max 10MB per file, keep 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    
    # Error file handler with rotation
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger

# Function to convert number to a string with seven digits
def convert_to_seven_digits(number):
    return f"{number:07d}"

def get_or_create_visit_count():
    """Reads or initializes the visit count from/to the database."""
    try:
        record = VisitCount.query.filter_by(id=1).with_for_update().first() # Use with_for_update for concurrency
        if not record:
            record = VisitCount(id=1, count=0)
            db.session.add(record)
            db.session.commit()
            # activity_logger.info("VisitCount record initialized in DB.")
        return record.count
    except Exception as ex:
        db.session.rollback() # Ensure rollback on error
        # error_logger.error(f"Failed to read/initialize visit count: {ex}")
        return 0
    