import logging
import uuid
from app.db import db

# Import centralized loggers
try:
    from app import activity_logger, access_logger, error_logger
except ImportError:
    activity_logger = logging.getLogger('activity')
    access_logger = logging.getLogger('access')
    error_logger = logging.getLogger('error')

class Block(db.Model):
    __tablename__ = "blocks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    short_name = db.Column(db.String(128))
    uuid = db.Column(db.String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    nrega_id = db.Column(db.String(8))
    state_id = db.Column(db.ForeignKey('states.id'), nullable=False)
    district_id = db.Column(db.ForeignKey('districts.id'), nullable=False)

    state = db.relationship("State_UT", back_populates='blocks')
    district = db.relationship("District", back_populates='blocks')
    users = db.relationship('User', back_populates='block')
    
    def __init__(self, name, short_name, nrega_id, state_id, district_id, u_uid=None):
        try:
            self.uuid = str(uuid.uuid4()) if u_uid is None else u_uid
            self.name = name
            self.short_name = short_name
            self.nrega_id = nrega_id
            self.state_id = state_id
            self.district_id = district_id
            activity_logger.info(f"Block inserted: {self.name} (uuid={self.uuid})")
        except Exception as ex:
            error_logger.error(f"Error inserting Block: {ex}")
    
    def __repr__(self):
        return f"<State(id={self.id}, name='{self.name}', short_name='{self.short_name}', \
            nrega_id='{self.nrega_id}'), state_id='{self.state_id}', district_id='{self.district_id}', uuid='{self.uuid}'>"
    def json(self):
        try:
            access_logger.info(f"Accessed Block json for id={self.id}")
            return {
                'id': self.id,
                'name': self.name,
                'short_name': self.short_name,
                'nrega_id': self.nrega_id,
                'state_id': self.state_id,
                'district_id': self.district_id,
                'uuid': self.uuid
            }
        except Exception as ex:
            error_logger.error(f"Error in json() for Block id={getattr(self, 'id', None)}: {ex}")
            return {}
    
    @classmethod
    def get_blocks(cls):
        return db.session.query(cls).all()
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()