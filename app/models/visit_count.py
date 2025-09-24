from app.db import db


class VisitCount(db.Model):
    __tablename__ = "visit_count"
    
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.BigInteger)

    def __init__(self, count):
        self.count = count

    def json(self):
        return {
            "id":self.id,
            "count": self.count
        }