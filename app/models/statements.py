from datetime import datetime, timezone
import uuid

from flask import json
from app.db import db


class Statement(db.Model):
    __tablename__ = 'statements'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_mbox = db.Column(db.String(255))
    actor_name = db.Column(db.String(255))
    verb_id = db.Column(db.String(255), nullable=False)
    verb_display = db.Column(db.String(255))
    object_id = db.Column(db.String(255), nullable=False)
    object_definition = db.Column(db.Text)
    result_completion = db.Column(db.Boolean)
    result_success = db.Column(db.Boolean)
    result_score_raw = db.Column(db.Float)
    result_score_min = db.Column(db.Float)
    result_score_max = db.Column(db.Float)
    result_score_scaled = db.Column(db.Float)
    context_instructor = db.Column(db.String(255))
    context_team = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    stored = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    authority = db.Column(db.String(255))
    version = db.Column(db.String(10), default='1.0.3')
    voided = db.Column(db.Boolean, default=False)
    raw_statement = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'actor': {
                'mbox': self.actor_mbox,
                'name': self.actor_name
            },
            'verb': {
                'id': self.verb_id,
                'display': {'en-US': self.verb_display}
            },
            'object': {
                'id': self.object_id,
                'definition': json.loads(self.object_definition) if self.object_definition else None
            },
            'result': {
                'completion': self.result_completion,
                'success': self.result_success,
                'score': {
                    'raw': self.result_score_raw,
                    'min': self.result_score_min,
                    'max': self.result_score_max,
                    'scaled': self.result_score_scaled
                } if any([self.result_score_raw, self.result_score_min, self.result_score_max, self.result_score_scaled]) else None
            },
            'context': {
                'instructor': self.context_instructor,
                'team': self.context_team
            } if any([self.context_instructor, self.context_team]) else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'stored': self.stored.isoformat() if self.stored else None,
            'authority': self.authority,
            'version': self.version,
            'voided': self.voided
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        return 