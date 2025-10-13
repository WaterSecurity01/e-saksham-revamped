from datetime import datetime, timezone

from app.db import db
from sqlalchemy import distinct, extract, func, and_, or_
import logging


class Feedback(db.Model):
    __tablename__ = "feedback"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    email = db.Column(db.String(128))
    subject = db.Column(db.String(128))
    message_category = db.Column(db.String(128))
    message = db.Column(db.String())
    rating = db.Column(db.Integer)
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def __init__(self, name, email, subject, message_category, message, rating, image_filename = None):
        try:
            self.subject = subject
            self.name = name
            self.email = email
            self.message = message
            self.message_category = message_category
            self.rating = rating
            self.image_filename = image_filename

        except Exception as ex:
            raise
    def json(self):
        try:
            return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'message': self.message,
                'message_category': self.message_category,
                'rating': self.rating,
                'subject': self.subject,
                'image_filename': self.image_filename
            }
        except Exception as ex:
            return {}

    @classmethod
    def get_feedback_by_id(cls, _id):
        try:
            query = cls.query.filter_by(id=_id).first()
            if query:
                return query.json()
            else:
                return None
        except Exception as ex:
            return None
    
    @classmethod
    def get_feedback_by_email(cls, _email):
        try:
            query = cls.query.filter_by(email=_email).first()
            if query:
                return query.json()
            else:
                return None
        except Exception as ex:
            return None

    @classmethod
    def get_average(cls):
        try:
            avg = db.session.query(db.func.avg(cls.rating)).filter(cls.rating > 0).scalar()
            return avg
        except Exception as ex:
            return None

    @classmethod
    def get_all(cls):
        try:
            query = cls.query.order_by(cls.id.desc())
            return query
        except Exception as ex:
            return []

    def save_to_db(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()

    @classmethod
    def delete_from_db(cls, _id):
        try:
            feedback = cls.query.filter_by(id=_id).first()
            if feedback:
                db.session.delete(feedback)
                db.session.commit()

        except Exception as ex:
            db.session.rollback()

    @staticmethod
    def commit_db():
        try:
            db.session.commit()
        except Exception as ex:
            db.session.rollback()

    @classmethod
    def update_db(cls, data, _id):
        try:
            feedback = cls.query.filter_by(id=_id).update(data)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
