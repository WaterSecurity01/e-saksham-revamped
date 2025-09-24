from datetime import datetime
from sqlalchemy import func
from app.db import db
import logging

# Centralized activity and error loggers
# try:
#     from app import activity_logger, error_logger
# except ImportError:
#     activity_logger = logging.getLogger('activity')
#     error_logger = logging.getLogger('error')

class UserCourse(db.Model):
    __tablename__ = 'user_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_issued = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __init__(self, user_id, course_id, certificate_issued, timestamp=None):
        try:
            if timestamp is None:
                timestamp = datetime.now()
            self.user_id = user_id
            self.course_id = course_id
            self.timestamp = timestamp
            self.certificate_issued = certificate_issued
            # activity_logger.info(f"User completed course: {self.course_id}, user_id={self.user_id}")
        except Exception as ex:
            # error_logger.error(f"Error saving status for User {user_id}: {ex}")
            pass

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'certificate_issued': self.certificate_issued,
            'timestamp': self.timestamp
        }
        
        
    @classmethod
    def find_by_user_and_course_id(cls, user_id, course_id):
        try:
            return cls.query.filter_by(user_id=user_id, course_id=course_id).first()
        except Exception as ex:
            # error_logger.error(f"Error finding CourseStatus for user_id={user_id}, course={course_id}: {ex}")
            return None
        
    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            # activity_logger.info(f"Saved CourseStatus for user_id={self.user_id}, course={self.course_id}")
        except Exception as ex:
            db.session.rollback()
            # error_logger.error(f"Error saving CourseStatus for user_id={self.user_id}, course={self.course_id}: {ex}")
            raise ex
    
    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            # activity_logger.info(f"Deleted CourseStatus for user_id={self.user_id}, course={self.course_id}")
        except Exception as ex:
            db.session.rollback()
            # error_logger.error(f"Error deleting CourseStatus for user_id={self.user_id}, course={self.course_id}: {ex}")
            raise ex
    
    def commit_db(self):
        try:
            db.session.commit()
            # activity_logger.info(f"Committed CourseStatus for user_id={self.user_id}, course={self.course_id}")
        except Exception as ex:
            db.session.rollback()
            # error_logger.error(f"Error committing CourseStatus for user_id={self.user_id}, course={self.course_id}: {ex}")
            raise ex
    
    def update_db(self, data):
        try:
            for key, value in data.items():
                setattr(self, key, value)
            self.commit_db()
            # activity_logger.info(f"Updated CourseStatus for user_id={self.user_id}, course={self.course_id}")
        except Exception as ex:
            # error_logger.error(f"Error updating CourseStatus for user_id={self.user_id}, course={self.course_id}: {ex}")
            raise ex
