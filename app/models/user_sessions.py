from zoneinfo import ZoneInfo
from app.db import db 
from datetime import datetime


class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    session_token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata")))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata")))
    user_agent = db.Column(db.String(256))
    ip_address = db.Column(db.String(45))
    is_active = db.Column(db.Boolean, default=True)


    def __init__(self, user_id, session_token, user_agent=None, ip_address=None):
        try:
            self.user_id = user_id
            self.session_token = session_token
            self.user_agent = user_agent
            self.ip_address = ip_address
            self.created_at = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
            self.last_seen = datetime.now(tz=ZoneInfo("Asia/Kolkata")) 
        except Exception as ex:
            raise
    def json(self):
        try:
            return {
                'id': self.id,
                'user_id': self.user_id,
                'session_token': self.session_token,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'last_seen': self.last_seen.isoformat() if self.last_seen else None,
                'user_agent': self.user_agent,
                'ip_address': self.ip_address,
                'is_active': self.is_active
            }
        except Exception as ex:
            return {}