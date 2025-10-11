from datetime import datetime, timezone

from app.db import db
from sqlalchemy import distinct, extract, func, and_, or_
import logging

# Import centralized loggers
try:
    from app import activity_logger, access_logger, error_logger
except ImportError:
    activity_logger = logging.getLogger('activity')
    access_logger = logging.getLogger('access')
    error_logger = logging.getLogger('error')

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
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __init__(self, name, email, subject, message_category, message, rating, image_filename = None):
        try:
            self.subject = subject
            self.name = name
            self.email = email
            self.message = message
            self.message_category = message_category
            self.rating = rating
            self.image_filename = image_filename
            activity_logger.info(
                f"Feedback initialized: from {self.name} ({self.email}), subject: {self.subject}, rating: {self.rating}"
            )
        except Exception as ex:
            error_logger.error(f"Error initializing Feedback: {ex}")

    def json(self):
        try:
            access_logger.info(f"Accessed feedback json for id={self.id}")
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
            error_logger.error(f"Error in json() for Feedback id={getattr(self, 'id', None)}: {ex}")
            return {}

    @classmethod
    def get_feedback_by_id(cls, _id):
        try:
            access_logger.info(f"Fetching feedback by id={_id}")
            query = cls.query.filter_by(id=_id).first()
            if query:
                activity_logger.info(f"Feedback found by id={_id}")
                return query.json()
            else:
                activity_logger.info(f"No feedback found by id={_id}")
                return None
        except Exception as ex:
            error_logger.error(f"Error fetching feedback by id={_id}: {ex}")
            return None
    
    @classmethod
    def get_feedback_by_email(cls, _email):
        try:
            access_logger.info(f"Fetching feedback by email={_email}")
            query = cls.query.filter_by(email=_email).first()
            if query:
                activity_logger.info(f"Feedback found by email={_email}")
                return query.json()
            else:
                activity_logger.info(f"No feedback found by email={_email}")
                return None
        except Exception as ex:
            error_logger.error(f"Error fetching feedback by email={_email}: {ex}")
            return None

    @classmethod
    def get_average(cls):
        try:
            access_logger.info("Calculating average feedback rating")
            avg = db.session.query(db.func.avg(cls.rating)).filter(cls.rating > 0).scalar()
            activity_logger.info(f"Average feedback rating calculated (excluding zero ratings): {avg}")
            return avg
        except Exception as ex:
            error_logger.error(f"Error calculating average feedback rating: {ex}")
            return None

    @classmethod
    def get_all(cls):
        try:
            access_logger.info("Fetching all feedback")
            query = cls.query.order_by(cls.id.desc())
            activity_logger.info("All feedback queried")
            return query
        except Exception as ex:
            error_logger.error(f"Error fetching all feedback: {ex}")
            return []

    def save_to_db(self):
        try:
            db.session.add(self)
            db.session.commit()
            activity_logger.info(f"Feedback saved to DB: id={self.id}, from {self.name} ({self.email})")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error saving feedback from {self.name} ({self.email}) to DB: {ex}")

    @classmethod
    def delete_from_db(cls, _id):
        try:
            feedback = cls.query.filter_by(id=_id).first()
            if feedback:
                db.session.delete(feedback)
                db.session.commit()
                activity_logger.info(f"Feedback deleted from DB: id={_id}")
            else:
                activity_logger.info(f"Attempted to delete non-existent feedback: id={_id}")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error deleting feedback id={_id} from DB: {ex}")

    @staticmethod
    def commit_db():
        try:
            db.session.commit()
            activity_logger.info("DB session committed (feedback).")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error committing DB session (feedback): {ex}")

    @classmethod
    def update_db(cls, data, _id):
        try:
            feedback = cls.query.filter_by(id=_id).update(data)
            db.session.commit()
            activity_logger.info(f"Feedback updated in DB: id={_id}, data={data}")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error updating feedback id={_id} in DB: {ex}")