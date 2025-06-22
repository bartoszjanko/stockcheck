from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from myproject.forum.models import Post, Comment
from myproject.forum.forms import PostForm, CommentForm
from myproject.companies.models import Company
from myproject import db
from myproject.admin.decorators import admin_required

from . import forum

@forum.route('/')
@login_required
def forum_main():
    companies = Company.query.order_by(Company.ticker).all()
    selected_company = request.args.get('company')
    query = Post.query.order_by(Post.created_at.desc())
    if selected_company:
        query = query.filter(Post.company_id == int(selected_company))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    posts_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = posts_pagination.items
    
    return render_template('/forum/forum.html', posts=posts, companies=companies, selected_company=selected_company, pagination=posts_pagination)

@forum.route('/add', methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()
    form.company.choices = [(c.id, f"{c.ticker} - {c.name}") for c in Company.query.order_by(Company.ticker)]
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            company_id=form.company.data,
            title=form.title.data,
            content=form.content.data
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('forum.forum_main'))
    return render_template('forum/add_post.html', form=form)

@forum.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            post_id=post.id,
            user_id=current_user.id,
            content=form.content.data
        )
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('forum.post_detail', post_id=post.id))
    return render_template('forum/post_detail.html', post=post, form=form)

@forum.route('/forum/post/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('forum.forum_main'))

@forum.route('/forum/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('forum.post_detail', post_id=post_id))