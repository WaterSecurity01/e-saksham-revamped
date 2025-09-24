from flask import Blueprint, current_app, jsonify, request, session
from app.models import State_UT,District,Block

blp = Blueprint('api', __name__, url_prefix='/api')

@blp.route("/states", methods=['GET'])
def states():
    states = State_UT.query.all()
    state_list = [{"id": d.id, "name": d.name} for d in states]

    return jsonify(state_list), 200

@blp.route("/districts")
def districts():
    state_id = request.args.get("state_id", type=int)

    if not state_id:
        return jsonify({"error": "state_id is required"}), 400
    district_list = [{"id": -1, "name": "--STATE OFFICIAL--"}]
    districts = District.query.filter_by(state_id=state_id).all()
    for d in districts:
        district_list.append({"id": d.id, "name": d.name})

    return jsonify(district_list), 200

@blp.route("/blocks")
def blocks():
    district_id = request.args.get("district_id", type=int)

    if not district_id:
        return jsonify({"error": "district_id is required"}), 400    

    block_list = [{"id": -1, "name": "-- DISTRICT OFFICIAL --"}]
    if district_id==-1:
        block_list = [{"id": -1, "name": "-- STATE OFFICIAL --"}]
    else:
        blocks = Block.query.filter_by(district_id=district_id).all()
        for b in blocks:
            block_list.append({"id": b.id, "name": b.name})

    return jsonify(block_list), 200

@blp.route('/decrypt_keys')
def decrypt_keys():
    # get your keys from wherever you store them
    public_key = current_app.config.get('PUBLIC_KEY')
    return jsonify({'publicKey': public_key}), 200

