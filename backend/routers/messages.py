
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from auth import CurrentUser, get_user_from_token_param
import models, schemas

router = APIRouter(prefix="/api/messages", tags=["messages"])


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws

    def disconnect(self, user_id: int):
        self.active.pop(user_id, None)

    async def send_to(self, user_id: int, data: dict):
        ws = self.active.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Annotated[str, Query()]):
    db: Session = SessionLocal()
    user = None
    try:
        user = get_user_from_token_param(token, db)
        if not user:
            await websocket.close(code=4001)
            return

        await manager.connect(user.id, websocket)
        user.is_online = True
        db.commit()

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                to_id = int(data["to"])
                text  = str(data["text"]).strip()
                if not text:
                    continue
            except (KeyError, ValueError, json.JSONDecodeError):
                await websocket.send_text(json.dumps({"error": "Неверный формат"}))
                continue

            receiver = db.get(models.User, to_id)
            if not receiver:
                await websocket.send_text(json.dumps({"error": "Пользователь не найден"}))
                continue

            msg = models.Message(sender_id=user.id, receiver_id=to_id, text=text)
            db.add(msg)
            db.commit()
            db.refresh(msg)

            payload = {
                "id": msg.id, "sender_id": msg.sender_id, "receiver_id": msg.receiver_id,
                "text": msg.text, "is_read": msg.is_read, "created_at": msg.created_at.isoformat(),
            }
            await manager.send_to(user.id, payload)
            await manager.send_to(to_id, payload)

    except WebSocketDisconnect:
        pass
    finally:
        if user:
            manager.disconnect(user.id)
            user.is_online = False
            db.commit()
        db.close()


@router.get("/dialogs", response_model=list[schemas.DialogOut])
def get_dialogs(current_user: CurrentUser, db: Session = Depends(get_db)):
    all_msgs = (
        db.query(models.Message)
        .filter(
            or_(models.Message.sender_id == current_user.id, models.Message.receiver_id == current_user.id)
        )
        .order_by(models.Message.created_at.desc())
        .all()
    )
    seen: set[int] = set()
    dialogs = []
    for msg in all_msgs:
        partner_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if partner_id in seen:
            continue
        seen.add(partner_id)
        partner = db.get(models.User, partner_id)
        unread = (
            db.query(models.Message)
            .filter(
                models.Message.sender_id == partner_id,
                models.Message.receiver_id == current_user.id,
                models.Message.is_read == False,
            )
            .count()
        )
        dialogs.append(schemas.DialogOut(partner=partner, last_message=msg, unread_count=unread))
    return dialogs


@router.get("/history/{user_id}", response_model=list[schemas.MessageOut])
def get_history(user_id: int, skip: int = 0, limit: int = 50, current_user: CurrentUser = ..., db: Session = Depends(get_db)):
    other = db.get(models.User, user_id)
    if not other:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    msgs = (
        db.query(models.Message)
        .filter(
            or_(
                and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == user_id),
                and_(models.Message.sender_id == user_id, models.Message.receiver_id == current_user.id),
            )
        )
        .order_by(models.Message.created_at.asc())
        .offset(skip).limit(limit).all()
    )
    for m in msgs:
        if m.receiver_id == current_user.id and not m.is_read:
            m.is_read = True
    db.commit()
    return msgs
