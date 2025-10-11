from app.db import db
from sqlalchemy import distinct, extract, func, and_, or_


class Video(db.Model):
    __tablename__ = "videos"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    length = db.Column(db.String(128))
    embed_url = db.Column(db.String(256))
    is_short = db.Column(db.Boolean, default=False)
    is_how_to = db.Column(db.Boolean, default=True)
    
    def __init__(self, title, length, embed_url, is_short, is_how_to=True):
        try:
            self.length = length
            self.title = title
            self.embed_url = embed_url
            self.is_short = is_short
            self.is_how_to = is_how_to
        except Exception as ex:
            raise ex

    def json(self):
        try:
            return {
                'id': self.id,
                'title': self.title,
                'embed_url': self.embed_url,
                'length': self.length,
                'is_short': self.is_short,
                'is_how_to': self.is_how_to
            }
        except Exception as ex:
            return {}

    
    @classmethod
    def get_chapters_by_id(cls, _id):
        try:
            query = cls.query.filter_by(id=_id).first()
            if query:
                return query.json()
            else:
                return None
        except Exception as ex:
            return None
        
    @classmethod
    def get_chapters_by_title(cls, _title):
        try:
            query = cls.query.filter_by(title=_title).first()
            if query:
                return query.json()
            else:
                return None
        except Exception as ex:
            return None

    @classmethod
    def get_all(cls):
        try:
            query = cls.query.order_by(cls.id)
            json_data = []
            for item in query:
                json_data.append(item.json())  # Ensure json method works
            return json_data
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
            videos = cls.query.filter_by(id=_id).first()
            if videos:
                db.session.delete(videos)
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
            videos = cls.query.filter_by(id=_id).update(data)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            
