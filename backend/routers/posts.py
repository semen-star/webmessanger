
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import CurrentUser
import models, schemas

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _enrich(post: models.Post, current_user: models.User) -> schemas.PostOut:
    liked = any(l.user_id == current_user.id for l in post.likes)
    return schemas.PostOut(
        id             = post.id,
        text           = post.text,
        created_at     = post.created_at,
        author         = post.author,
        likes_count    = len(post.likes),
        comments_count = len(post.comments),
        liked_by_me    = liked,
    )


@router.get("/feed", response_model=list[schemas.PostOut])
def get_feed(skip: int = 0, limit: int = 20, current_user: CurrentUser = ..., db: Session = Depends(get_db)):
    friendships = (
        db.query(models.Friendship)
        .filter(
            ((models.Friendship.requester_id == current_user.id) |
             (models.Friendship.addressee_id == current_user.id)),
            models.Friendship.status == "accepted",
        )
        .all()
    )
    friend_ids = set()
    for fs in friendships:
        friend_ids.add(fs.addressee_id if fs.requester_id == current_user.id else fs.requester_id)
    friend_ids.add(current_user.id)

    posts = (
        db.query(models.Post)
        .filter(models.Post.author_id.in_(friend_ids))
        .order_by(models.Post.created_at.desc())
        .offset(skip).limit(limit).all()
    )
    return [_enrich(p, current_user) for p in posts]


@router.post("", response_model=schemas.PostOut, status_code=201)
def create_post(body: schemas.PostCreate, current_user: CurrentUser, db: Session = Depends(get_db)):
    post = models.Post(author_id=current_user.id, text=body.text)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _enrich(post, current_user)


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нельзя удалить чужой пост")
    db.delete(post)
    db.commit()


@router.post("/{post_id}/like", response_model=schemas.PostOut)
def toggle_like(post_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    like = (
        db.query(models.Like)
        .filter(models.Like.user_id == current_user.id, models.Like.post_id == post_id)
        .first()
    )
    if like:
        db.delete(like)
    else:
        db.add(models.Like(user_id=current_user.id, post_id=post_id))
    db.commit()
    db.refresh(post)
    return _enrich(post, current_user)


@router.get("/{post_id}/comments", response_model=list[schemas.CommentOut])
def get_comments(post_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return post.comments


@router.post("/{post_id}/comments", response_model=schemas.CommentOut, status_code=201)
def add_comment(post_id: int, body: schemas.CommentCreate, current_user: CurrentUser, db: Session = Depends(get_db)):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    comment = models.Comment(post_id=post_id, author_id=current_user.id, text=body.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
