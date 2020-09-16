import pytz
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flaskBlog import db, app
from flaskBlog import loginManager
from datetime import datetime
from flask_login import UserMixin

@loginManager.user_loader
def loadUser(userId):
    return User.query.get(int(userId))
  
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=1)
    username = db.Column(db.String(20), unique=1, nullable=0)
    email = db.Column(db.String(100), unique=1, nullable=0)
    image = db.Column(db.String(20), nullable=0, default='default.jpg')
    password = db.Column(db.String(60), nullable=0)
    posts = db.relationship('Post', backref='auther', lazy=1)
    comments = db.relationship('Comment', backref='auther', lazy=1)    

    def getResetToken(self, expires = 1800):
        s = Serializer(app.config['SECRET_KEY'], expires)
        return s.dumps({'userId': self.id}).decode('utf-8')

    @staticmethod
    def verifyResetToken(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            userId = s.loads(token)['userId']
        except:
            return None
        return User.query.get(userId)

    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    title = db.Column(db.String(100), nullable=0)
    date = db.Column(db.DateTime, nullable=0, default=datetime.now(pytz.timezone('Asia/Kolkata')))
    content = db.Column(db.Text, nullable=0)
    userId = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=0) 
    def __repr__(self):
        return f"User('{self.title}','{self.date}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    content = db.Column(db.Text, nullable=0)
    userId = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=0)
    postId = db.Column(db.Integer, nullable=0)