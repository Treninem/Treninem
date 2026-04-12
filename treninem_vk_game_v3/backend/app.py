from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, game_logic
from .config import (
    ADMIN_PASSWORD,
    ALLOW_DEV_LOGIN,
    APP_TITLE,
    CREATOR_NAME,
    OWNER_VK_IDS,
    PUBLIC_WEB_URL,
    STATIC_DIR,
    VK_APP_ID,
    VK_APP_SECRET,
)
from .seed_data import CHARACTERS, CATEGORIES, EFFECT_KINDS, EQUIP_SLOTS, RARITIES

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
db.init_db()


class VkLoginPayload(BaseModel):
    launch_params: str | None = None
    dev_vk_user_id: int | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class CharacterPayload(BaseModel):
    character_key: str


class ItemPayload(BaseModel):
    item_code: str


class ExpeditionPayload(BaseModel):
    difficulty: str


class DungeonPayload(BaseModel):
    floor: int
    difficulty: str


class CraftPayload(BaseModel):
    recipe_code: str


class MarketPayload(BaseModel):
    item_code: str
    quantity: int
    price: int


class BuyPayload(BaseModel):
    listing_id: int


class PvPPayload(BaseModel):
    opponent_user_id: int


class GiftPayload(BaseModel):
    to_user_id: int
    item_code: str
    quantity: int


class AdminAuthPayload(BaseModel):
    password: str


class AdminGiveGoldPayload(BaseModel):
    target_user_id: int
    amount: int


class AdminGiveItemPayload(BaseModel):
    target_user_id: int
    item_code: str
    quantity: int


class AdminRemoveItemPayload(BaseModel):
    target_user_id: int
    item_code: str
    quantity: int


class AdminBanPayload(BaseModel):
    target_user_id: int
    banned: bool


class AdminLevelPayload(BaseModel):
    target_user_id: int
    level: int


class AdminSetAdminPayload(BaseModel):
    target_user_id: int
    is_admin: bool


class CreateItemPayload(BaseModel):
    item_code: str
    name: str
    category: str
    rarity: str
    description: str
    weight: float
    price: int
    effect_kind: str
    effect_stat: str = ''
    effect_value: int = 0
    effect_duration: int = 0
    equip_slot: str = ''
    is_consumable: int = 0
    is_stackable: int = 1
    icon: str = '✨'


class DeleteItemDefPayload(BaseModel):
    item_code: str


class AndroidLinkPayload(BaseModel):
    code: str


class BankRepayPayload(BaseModel):
    amount: int | None = None


class QuestClaimPayload(BaseModel):
    quest_code: str


def verify_vk_launch_params(raw_query: str) -> Dict[str, str]:
    params = dict(parse_qsl(raw_query.lstrip('?'), keep_blank_values=True))
    sign = params.get('sign')
    if not sign:
        raise HTTPException(401, 'Не найден sign в launch params')
    ordered = {k: params[k] for k in sorted(p for p in params if p.startswith('vk_'))}
    if not ordered:
        raise HTTPException(401, 'Нет vk_* параметров')
    digest = hmac.new(VK_APP_SECRET.encode(), urlencode(ordered, doseq=True).encode(), hashlib.sha256).digest()
    encoded = base64.b64encode(digest).decode('utf-8').rstrip('=').replace('+', '-').replace('/', '_')
    if encoded != sign:
        raise HTTPException(401, 'Подпись launch params не прошла проверку')
    return params


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(401, 'Нет токена')
    token = authorization.replace('Bearer ', '').strip()
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Сессия недействительна')
    if user['is_banned']:
        raise HTTPException(403, 'Аккаунт заблокирован')
    return user


def require_admin(user: Dict[str, Any]):
    if not (user['is_admin'] or user.get('vk_user_id') in OWNER_VK_IDS):
        raise HTTPException(403, 'Недостаточно прав')


@app.get('/')
async def index():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/health')
async def health():
    return {'ok': True, 'title': APP_TITLE, 'creator': CREATOR_NAME}


@app.get('/api/meta')
async def meta():
    return {
        'title': APP_TITLE,
        'creator': CREATOR_NAME,
        'vk_app_id': VK_APP_ID,
        'public_web_url': PUBLIC_WEB_URL,
        'characters': CHARACTERS,
    }


@app.post('/api/auth/vk-login')
async def vk_login(payload: VkLoginPayload):
    if payload.launch_params:
        params = verify_vk_launch_params(payload.launch_params)
        vk_user_id = int(params['vk_user_id'])
        display_name = payload.display_name or f'VK User {vk_user_id}'
        avatar_url = payload.avatar_url or ''
    elif ALLOW_DEV_LOGIN and payload.dev_vk_user_id:
        vk_user_id = payload.dev_vk_user_id
        display_name = payload.display_name or f'Dev User {vk_user_id}'
        avatar_url = payload.avatar_url or ''
    else:
        raise HTTPException(400, 'Для входа нужны launch_params VK или dev_vk_user_id')
    user = db.get_or_create_user(vk_user_id, display_name, avatar_url)
    token = db.create_session(user['id'])
    return {'token': token, 'user': db.get_user(user['id'])}


@app.post('/api/auth/android-link')
async def android_link(payload: AndroidLinkPayload):
    try:
        return game_logic.bind_android_by_code(payload.code)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/me')
async def me(user=Depends(get_current_user)):
    return db.get_user(user['id'])


@app.post('/api/character/select')
async def choose_character(payload: CharacterPayload, user=Depends(get_current_user)):
    if db.get_user(user['id'])['character_key']:
        raise HTTPException(400, 'Персонаж уже выбран и не может быть изменён')
    try:
        db.set_character(user['id'], payload.character_key)
        return db.get_user(user['id'])
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/inventory')
async def inventory(user=Depends(get_current_user)):
    return db.list_inventory(user['id'])


@app.post('/api/items/use')
async def use_item_api(payload: ItemPayload, user=Depends(get_current_user)):
    try:
        return game_logic.use_item(user['id'], payload.item_code)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/items/equip')
async def equip_item_api(payload: ItemPayload, user=Depends(get_current_user)):
    try:
        return game_logic.equip_item(user['id'], payload.item_code)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/shop')
async def shop(user=Depends(get_current_user)):
    return db.get_shop_offers()


@app.post('/api/shop/buy/{offer_id}')
async def buy_shop(offer_id: int, user=Depends(get_current_user)):
    try:
        return game_logic.buy_shop_offer(user['id'], offer_id)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/expedition')
async def expedition(payload: ExpeditionPayload, user=Depends(get_current_user)):
    try:
        return game_logic.expedition(user['id'], payload.difficulty)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/dungeon')
async def dungeon(payload: DungeonPayload, user=Depends(get_current_user)):
    try:
        return game_logic.dungeon_run(user['id'], payload.floor, payload.difficulty)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/recipes')
async def recipes(user=Depends(get_current_user)):
    return db.get_recipes()


@app.post('/api/craft')
async def craft(payload: CraftPayload, user=Depends(get_current_user)):
    try:
        return game_logic.craft_recipe(user['id'], payload.recipe_code)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/market')
async def market(user=Depends(get_current_user)):
    return game_logic.get_market()


@app.post('/api/market/create')
async def market_create(payload: MarketPayload, user=Depends(get_current_user)):
    try:
        return game_logic.create_market_listing(user['id'], payload.item_code, payload.quantity, payload.price)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/market/buy')
async def market_buy(payload: BuyPayload, user=Depends(get_current_user)):
    try:
        return game_logic.buy_market_listing(user['id'], payload.listing_id)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/bank/status')
async def bank_status_api(user=Depends(get_current_user)):
    return game_logic.bank_status(user['id'])


@app.post('/api/bank/credit')
async def bank_credit(user=Depends(get_current_user)):
    try:
        return game_logic.bank_credit(user['id'])
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/bank/repay')
async def bank_repay(payload: BankRepayPayload, user=Depends(get_current_user)):
    try:
        return game_logic.repay_bank(user['id'], payload.amount)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/pvp')
async def pvp(payload: PvPPayload, user=Depends(get_current_user)):
    try:
        return game_logic.pvp_fight(user['id'], payload.opponent_user_id)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/gift')
async def gift(payload: GiftPayload, user=Depends(get_current_user)):
    try:
        return game_logic.gift_item(user['id'], payload.to_user_id, payload.item_code, payload.quantity)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/leaderboard')
async def leaderboard(user=Depends(get_current_user)):
    return game_logic.leaderboard()


@app.get('/api/activity')
async def activity(user=Depends(get_current_user)):
    return game_logic.activity_feed(user['id'])


@app.get('/api/daily')
async def daily(user=Depends(get_current_user)):
    return game_logic.daily_status(user['id'])


@app.post('/api/daily/claim')
async def daily_claim(user=Depends(get_current_user)):
    try:
        return game_logic.claim_daily(user['id'])
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/quests')
async def quests(user=Depends(get_current_user)):
    return game_logic.quests_status(user['id'])


@app.post('/api/quests/claim')
async def claim_quest(payload: QuestClaimPayload, user=Depends(get_current_user)):
    try:
        return game_logic.claim_quest(user['id'], payload.quest_code)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/link-code')
async def link_code(user=Depends(get_current_user)):
    return game_logic.generate_link_code(user['id'])


@app.post('/api/admin/auth')
async def admin_auth(payload: AdminAuthPayload, user=Depends(get_current_user)):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(403, 'Неверный пароль')
    require_admin(user)
    return {'ok': True}


@app.get('/api/admin/item-options')
async def admin_item_options(user=Depends(get_current_user)):
    require_admin(user)
    return {
        'categories': list(CATEGORIES.keys()) + ['currency'],
        'rarities': [r[0] for r in RARITIES],
        'effect_kinds': EFFECT_KINDS,
        'stats': ['hp', 'energy', 'attack', 'defense', 'speed', 'gold', 'exp', 'slots', 'weight_limit', ''],
        'equip_slots': [''] + EQUIP_SLOTS,
    }


@app.post('/api/admin/give-gold')
async def admin_give_gold(payload: AdminGiveGoldPayload, user=Depends(get_current_user)):
    require_admin(user)
    with db.get_conn() as conn:
        conn.execute('UPDATE users SET gold=gold+? WHERE id=?', (payload.amount, payload.target_user_id))
        db.record_activity(conn, payload.target_user_id, 'admin_gold', {'amount': payload.amount})
    db.log_admin(user['id'], 'give_gold', payload.dict())
    return {'ok': True}


@app.post('/api/admin/give-item')
async def admin_give_item(payload: AdminGiveItemPayload, user=Depends(get_current_user)):
    require_admin(user)
    try:
        with db.get_conn() as conn:
            db.add_item(conn, payload.target_user_id, payload.item_code, payload.quantity)
            db.record_activity(conn, payload.target_user_id, 'admin_item', {'item_code': payload.item_code, 'quantity': payload.quantity})
        db.log_admin(user['id'], 'give_item', payload.dict())
        return {'ok': True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/admin/remove-item')
async def admin_remove_item(payload: AdminRemoveItemPayload, user=Depends(get_current_user)):
    require_admin(user)
    try:
        with db.get_conn() as conn:
            db.remove_any_item_for_admin(conn, payload.target_user_id, payload.item_code, payload.quantity)
            db.record_activity(conn, payload.target_user_id, 'admin_item_removed', {'item_code': payload.item_code, 'quantity': payload.quantity})
        db.log_admin(user['id'], 'remove_item', payload.dict())
        return {'ok': True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/admin/ban')
async def admin_ban(payload: AdminBanPayload, user=Depends(get_current_user)):
    require_admin(user)
    with db.get_conn() as conn:
        if OWNER_VK_IDS:
            placeholders = ','.join('?' * len(OWNER_VK_IDS))
            conn.execute(
                f'UPDATE users SET is_banned=? WHERE id=? AND COALESCE(vk_user_id, 0) NOT IN ({placeholders})',
                (1 if payload.banned else 0, payload.target_user_id, *OWNER_VK_IDS),
            )
        else:
            conn.execute('UPDATE users SET is_banned=? WHERE id=?', (1 if payload.banned else 0, payload.target_user_id))
    db.log_admin(user['id'], 'ban_toggle', payload.dict())
    return {'ok': True}


@app.post('/api/admin/set-level')
async def admin_set_level(payload: AdminLevelPayload, user=Depends(get_current_user)):
    require_admin(user)
    level = max(1, min(100, payload.level))
    with db.get_conn() as conn:
        conn.execute('UPDATE users SET level=? WHERE id=?', (level, payload.target_user_id))
        db.recalc_stats(conn, payload.target_user_id)
        db.record_activity(conn, payload.target_user_id, 'admin_level', {'level': level})
    db.log_admin(user['id'], 'set_level', payload.dict())
    return {'ok': True}


@app.post('/api/admin/set-admin')
async def admin_set_admin(payload: AdminSetAdminPayload, user=Depends(get_current_user)):
    if user.get('vk_user_id') not in OWNER_VK_IDS:
        raise HTTPException(403, 'Только владелец может менять админов')
    with db.get_conn() as conn:
        conn.execute('UPDATE users SET is_admin=? WHERE id=?', (1 if payload.is_admin else 0, payload.target_user_id))
    db.log_admin(user['id'], 'set_admin', payload.dict())
    return {'ok': True}


@app.post('/api/admin/create-item')
async def admin_create_item(payload: CreateItemPayload, user=Depends(get_current_user)):
    require_admin(user)
    try:
        with db.get_conn() as conn:
            conn.execute(
                '''INSERT INTO item_defs (
                    item_code, name, category, rarity, description, weight, price, effect_kind, effect_stat,
                    effect_value, effect_duration, equip_slot, is_consumable, is_stackable, icon, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
                (
                    payload.item_code, payload.name, payload.category, payload.rarity, payload.description,
                    payload.weight, payload.price, payload.effect_kind, payload.effect_stat, payload.effect_value,
                    payload.effect_duration, payload.equip_slot, payload.is_consumable, payload.is_stackable, payload.icon,
                ),
            )
        db.log_admin(user['id'], 'create_item', payload.dict())
        return {'ok': True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/admin/delete-item-def')
async def admin_delete_item_def(payload: DeleteItemDefPayload, user=Depends(get_current_user)):
    require_admin(user)
    try:
        db.delete_custom_item_definition(payload.item_code)
        db.log_admin(user['id'], 'delete_item_def', payload.dict())
        return {'ok': True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/admin/users')
async def admin_users(user=Depends(get_current_user)):
    require_admin(user)
    with db.get_conn() as conn:
        rows = conn.execute(
            'SELECT id, vk_user_id, display_name, level, gold, bank_debt, is_banned, is_admin FROM users ORDER BY id DESC LIMIT 300'
        ).fetchall()
        return [dict(r) for r in rows]


@app.get('/api/admin/logs')
async def admin_logs(user=Depends(get_current_user)):
    require_admin(user)
    return db.get_admin_logs(limit=120)


@app.get('/api/items/all')
async def all_items(user=Depends(get_current_user)):
    return db.get_item_definitions()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
    return JSONResponse(status_code=500, content={'detail': str(exc)})
