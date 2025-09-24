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

class State_UT(db.Model):
    __tablename__ = "states"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    short_name = db.Column(db.String(128))
    uuid = db.Column(db.String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    nrega_id = db.Column(db.String(4))

    districts = db.relationship('District', back_populates='state')
    blocks = db.relationship('Block', back_populates='state')
    users = db.relationship('User', back_populates='state')
    
    def __init__(self, name, short_name, nrega_id, u_uid=None):
        try:
            self.uuid = str(uuid.uuid4()) if u_uid is None else u_uid
            self.name = name
            self.short_name = short_name
            self.nrega_id = nrega_id
            activity_logger.info(f"State or UT inserted: {self.name} (uuid={self.uuid})")
        except Exception as ex:
            error_logger.error(f"Error inserting State or UT: {ex}")

    def json(self):
        try:
            access_logger.info(f"Accessed state or ut json for id={self.id}")
            return {
                'id': self.id,
                'name': self.name,
                'short_name': self.short_name,
                'nrega_id': self.nrega_id,
                'uuid': self.uuid
            }
        except Exception as ex:
            error_logger.error(f"Error in json() for state or ut id={getattr(self, 'id', None)}: {ex}")
            return {}
        
    @classmethod
    def get_states(cls):
        return db.session.query(cls).all()
      
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()