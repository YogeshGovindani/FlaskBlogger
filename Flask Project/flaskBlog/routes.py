import secrets
import os
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskBlog.form import (registrationForm, loginForm, updateAccountForm, 
                            PostForm, RequestResetForm,  ResetPassword, CommentForm)
from flaskBlog.models import User, Post, Comment
from flaskBlog import app
from flaskBlog import bcrypt
from flaskBlog import db
from flask_login import login_user, current_user, logout_user, login_required
import smtplib

@app.route('/')
@app.route('/home')         
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.id.desc()).paginate(per_page=3, page=page)
    return render_template('home.html', posts=posts)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = registrationForm()
    if form.validate_on_submit():
        hashedPassword = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        username = form.username.data
        email = form.email.data
        user = User(username=username, email=email, password=hashedPassword)
        db.session.add(user)
        db.session.commit()
        flash(f'Account Created for {form.username.data}, you can now login')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = loginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            nextPage = request.args.get('next')
            if nextPage:
                return redirect(nextPage)
            else:
                return redirect(url_for('home'))
        else:
            flash(f'Invalid Email or password')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You are now logged out')
    return redirect(url_for('home'))

def savePicture(formPicture):
    randomHex = secrets.token_hex(8)
    _, ext = os.path.splitext(formPicture.filename)
    pictureFileName = randomHex + ext
    picturePath = os.path.join(app.root_path, 'static/profilePics', pictureFileName)
    outputSize = (200, 200)
    formPicture = Image.open(formPicture)
    formPicture.thumbnail(outputSize)
    formPicture.save(picturePath)
    return pictureFileName


@app.route('/account', methods=['POST', 'GET'])
@login_required
def account():
    form = updateAccountForm() 
    if form.validate_on_submit():
        if form.picture.data:
            pictureFile = savePicture(form.picture.data)
            current_user.image = pictureFile
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image = url_for('static' ,filename='profilePics/'+current_user.image)
    return render_template('account.html', image=image, form=form)

@app.route('/newpost', methods=['POST', 'GET'])
@login_required
def newpost():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, auther=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post has been created')
        return redirect(url_for('home'))
    return render_template('newPost.html', form=form, legend='Create New Post')

@app.route('/post/<postId>')
def post(postId):
    post = Post.query.get_or_404(postId)
    comments = Comment.query.filter_by(postId=postId).all()
    t=''
    return render_template('post.html', post=post, comments=comments, t=t)

@app.route('/post/<postId>/update', methods=['POST', 'GET'])
def postUpdate(postId):
    post = Post.query.get_or_404(postId)
    if post.auther != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated')
        return redirect(url_for('post',postId=postId))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('newPost.html', form=form, legend='Update Post')

@app.route('/post/<postId>/delete', methods=['POST', 'GET'])
def deletePost(postId):
    post = Post.query.get_or_404(postId)
    if post.auther != current_user:
        abort(403)
    comments = Comment.query.filter_by(postId=postId).all()
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted')
    return redirect(url_for('home'))

@app.route('/user/<username>')
def user(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(auther=user)\
        .order_by(Post.id.desc()).paginate(per_page=3, page=page)
    return render_template('user.html', posts=posts, user=user)

def sendResetEmail(user):
    token = user.getResetToken()
    msg = f''' Reset Password \n\n
    To reset your password visit the following link:
    {url_for('resetToken', token= token, _external=1)}

    If you did not make this request, please ignore this email.
    '''
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("yogeshgovindani09@gmail.com", "")
    server.sendmail("noreply@gmail.com", user.email, msg)

@app.route('/resetpassword', methods=['POST', 'GET'])
def resetRequest():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email= form.email.data).first()
        sendResetEmail(user)
        flash('An email has been sent to you with instructions for reseting the password')
        return redirect(url_for('login'))
    return render_template('resetRequest.html', form=form)


@app.route('/resetpassword/<token>', methods=['POST', 'GET'])
def resetToken(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verifyResetToken(token)
    if user is None:
        flash('That is an Invalid or Expired Token')
        return redirect(url_for('resetpassword'))
    form = ResetPassword()
    if form.validate_on_submit():
        hashedPassword = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashedPassword
        db.session.commit()
        flash(f'Password updated for {user.username}, you can now login')
        return redirect(url_for('login'))
    return render_template('resetToken.html', form=form)

@app.route('/comment/<postId>', methods=['POST', 'GET'])
@login_required
def comment(postId):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.comment.data, auther=current_user, postId=int(postId))
        db.session.add(comment)
        db.session.commit()
        flash('Comment has been added')
        return redirect(url_for('post',postId=postId))
    return render_template('comment.html', form=form)