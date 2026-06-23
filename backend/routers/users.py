
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import CurrentUser
import models, schemas

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_me(body: schemas.UpdateProfileRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.avatar is not None:
        current_user.avatar = body.avatar
    if body.bio is not None:
        current_user.bio = body.bio
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/search", response_model=list[schemas.UserShort])
def search_users(q: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    like = f"%{q.lower()}%"
    users = (
        db.query(models.User)
        .filter(
            (models.User.username.ilike(like)) |
            (models.User.display_name.ilike(like))
        )
        .filter(models.User.id != current_user.id)
        .limit(20)
        .all()
    )
    return users


@router.get("/me/friends", response_model=list[schemas.UserShort])
def my_friends(current_user: CurrentUser, db: Session = Depends(get_db)):
    friendships = (
        db.query(models.Friendship)
        .filter(
            ((models.Friendship.requester_id == current_user.id) |
             (models.Friendship.addressee_id == current_user.id)),
            models.Friendship.status == "accepted",
        )
        .all()
    )
    friends = []
    for fs in friendships:
        partner = fs.addressee if fs.requester_id == current_user.id else fs.requester
        friends.append(partner)
    return friends


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.post("/{user_id}/friend-request", response_model=schemas.FriendshipOut, status_code=201)
def send_friend_request(user_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя добавить себя в друзья")
    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    existing = (
        db.query(models.Friendship)
        .filter(
            ((models.Friendship.requester_id == current_user.id) & (models.Friendship.addressee_id == user_id)) |
            ((models.Friendship.requester_id == user_id) & (models.Friendship.addressee_id == current_user.id))
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Заявка уже существует")
    fs = models.Friendship(requester_id=current_user.id, addressee_id=user_id)
    db.add(fs)
    db.commit()
    db.refresh(fs)
    return fs


@router.patch("/friend-request/{request_id}", response_model=schemas.FriendshipOut)
def respond_friend_request(
    request_id: int, action: str, current_user: CurrentUser, db: Session = Depends(get_db),
):
    fs = db.get(models.Friendship, request_id)
    if not fs or fs.addressee_id != current_user.id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action: 'accept' или 'decline'")
    fs.status = "accepted" if action == "accept" else "declined"
    db.commit()
    db.refresh(fs)
    return fs
