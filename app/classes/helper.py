import base64
import csv
from functools import wraps
import logging
import os
import random
import re

from flask import abort, current_app, json, jsonify, request, session
import urllib

from flask_login import current_user
from app.classes.logging import get_route_loggers
from app.db import db
from app.models import State_UT, District, Block, User

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

from app.models.visit_count import VisitCount

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

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
        json_string = json.dumps(correct_payload, separators=(",", ":"))

        # URL-encode the JSON string
        encoded_string = urllib.parse.quote(json_string, safe='')

        # Construct the final URL
        return f"slxapi={encoded_string}"

        # return jsonify({"url": final_url})

    except Exception as e:
        return None
    
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
    
def extract_youtube_video_id_from_any_url(url):
    """
    Extract video ID from any YouTube URL format
    """
    if not url:
        return None
    
    # Various YouTube URL patterns
    patterns = [
        # Regular watch URLs with parameters
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        # Shorts URLs
        r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        # Embed URLs
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        # Short URLs (youtu.be)
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        # Mobile URLs
        r'(?:m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def convert_to_embed_url(url):
    """
    Convert any YouTube URL to embed format
    """
    if not url:
        return None
    
    video_id = extract_youtube_video_id_from_any_url(url)
    if not video_id:
        return None
    
    return f"https://www.youtube.com/embed/{video_id}"

def is_youtube_shorts_url(url):
    """
    Check if the URL is a YouTube Shorts URL
    """
    if not url:
        return False
    
    return '/shorts/' in url or 'youtube.com/shorts' in url

def validate_youtube_embed_url(url):
    """
    Validate if the provided URL is a valid YouTube embed URL
    """
    if not url:
        return False
    
    # YouTube embed URL patterns (more flexible)
    embed_patterns = [
        r'^https://www\.youtube\.com/embed/[a-zA-Z0-9_-]+',
        r'^https://youtube\.com/embed/[a-zA-Z0-9_-]+',
        r'^http://www\.youtube\.com/embed/[a-zA-Z0-9_-]+',
        r'^http://youtube\.com/embed/[a-zA-Z0-9_-]+',
    ]
    
    for pattern in embed_patterns:
        if re.match(pattern, url):
            return True
    
    return False

def extract_youtube_video_id(embed_url):
    """
    Extract video ID from YouTube embed URL
    """
    if not embed_url:
        return None
    
    # Pattern to extract video ID from embed URL
    pattern = r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, embed_url)
    
    if match:
        return match.group(1)
    
    return None

def validate_any_youtube_url(url):
    """
    Validate if the provided URL is any valid YouTube URL format
    """
    if not url:
        return False
    
    # Check if it's a YouTube domain
    youtube_domains = [
        'youtube.com',
        'www.youtube.com', 
        'm.youtube.com',
        'youtu.be'
    ]
    
    # Check if URL contains any YouTube domain
    has_youtube_domain = any(domain in url.lower() for domain in youtube_domains)
    if not has_youtube_domain:
        return False
    
    # Try to extract video ID - if successful, it's a valid YouTube URL
    video_id = extract_youtube_video_id_from_any_url(url)
    return video_id is not None

def orm_to_dict_list(queryset, fields):
    """Convert ORM objects into list of dicts with only required fields."""
    return [{f: getattr(obj, f) for f in fields} for obj in queryset]

def _build_enriched_options(model, fields, enabled_ids):
    """Return ordered option dictionaries including disabled flags for search results."""
    fetch_fields = set(fields) | {"id"}
    options = []

    for obj in model.query.order_by(model.id).all():
        option = {field: getattr(obj, field) for field in fetch_fields}
        option["disabled"] = obj.id not in enabled_ids
        options.append(option)

    options.sort(key=lambda record: (record["disabled"], record["id"]))
    return options