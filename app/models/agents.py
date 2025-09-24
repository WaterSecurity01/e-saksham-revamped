from datetime import datetime, timezone
from app.db import db


class Agent(db.Model):
    __tablename__ = 'agents'
    
    id = db.Column(db.Integer, primary_key=True)
    mbox = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def save(self):
        db.session.add(self)
        db.session.commit()
        return
