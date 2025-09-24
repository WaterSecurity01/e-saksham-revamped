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

class District(db.Model):
    __tablename__ = "districts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    short_name = db.Column(db.String(128))
    uuid = db.Column(db.String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    nrega_id = db.Column(db.String(4))
    state_id = db.Column(db.ForeignKey('states.id'), nullable=False)

    state = db.relationship("State_UT", back_populates="districts")
    blocks = db.relationship("Block", back_populates="district")
    users = db.relationship("User", back_populates='district')
    
    def __init__(self, name, short_name, nrega_id, state_id, u_uid=None):
        try:
            self.uuid = str(uuid.uuid4()) if u_uid is None else u_uid
            self.name = name
            self.short_name = short_name
            self.nrega_id = nrega_id
            self.state_id = state_id
            activity_logger.info(f"District inserted: {self.name} (uuid={self.uuid})")
        except Exception as ex:
            error_logger.error(f"Error inserting District: {ex}")

    def json(self):
        try:
            access_logger.info(f"Accessed District json for id={self.id}")
            return {
                'id': self.id,
                'name': self.name,
                'short_name': self.short_name,
                'nrega_id': self.nrega_id,
                'state_id': self.state_id,
                'uuid': self.uuid
            }
        except Exception as ex:
            error_logger.error(f"Error in json() for District id={getattr(self, 'id', None)}: {ex}")
            return {}
        
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()