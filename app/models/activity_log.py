from datetime import datetime
from zoneinfo import ZoneInfo
from app.db import db
import logging
from sqlalchemy import event

# Centralized activity and error loggers
try:
    from app import activity_logger, error_logger
except ImportError:
    activity_logger = logging.getLogger('activity')
    error_logger = logging.getLogger('error')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(tz=ZoneInfo('Asia/Kolkata')), nullable=False)
    
    def __repr__(self):
        return f'<Activity: {self.action}>'

# SQLAlchemy event to log automatically on insert
@event.listens_for(ActivityLog, "after_insert")
def log_activity(mapper, connection, target):
    try:
        msg = f"User {target.user_id} performed: {target.action} at {target.timestamp}"
        activity_logger.info(msg)
    except Exception as ex:
        error_logger.error(f"Failed to log activity: {ex}")