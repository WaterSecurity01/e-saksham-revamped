from datetime import datetime, timezone

from sqlalchemy import func
from app.db import db


class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    type = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=func.now())

    def save(self):
        db.session.add(self)
        db.session.commit()
        return
