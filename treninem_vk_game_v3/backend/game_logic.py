from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from . import db


def _ready_in(conn, user_id: int, action_key: str) -> int:
    row = conn.execute('SELECT ready_at FROM cooldowns WHERE user_id=? AND action_key=?', (user_id, action_key)).fetchone()
    if not row:
        return 0
    remaining = int((datetime.fromisoformat(row['ready_at']) - db.utcnow()).total_seconds())
    return max(0, remaining)


def _set_cd(conn, user_id: int, action_key: str, seconds: int):
    conn.execute(
        'INSERT OR REPLACE INTO cooldowns (user_id, action_key, ready_at) VALUES (?, ?, ?)',
        (user_id, action_key, (db.utcnow() + timedelta(seconds=seconds)).isoformat()),
    )


def exp_for_next_level(level: int) -> int:
    if level >= 100:
        return 10**9
    if level <= 50:
        return 80 + level * 22
    return int(1180 + ((level - 50) ** 2.1) * 18)


def _apply_levelups(conn, user_id: int):
    while True:
        row = conn.execute('SELECT level, exp FROM users WHERE id=?', (user_id,)).fetchone()
        if not row:
            return
        need = exp_for_next_level(int(row['level']))
        if int(row['level']) >= 100 or int(row['exp']) < need:
            return
        conn.execute('UPDATE users SET exp = exp - ?, level = level + 1 WHERE id=?', (need, user_id))
        db.recalc_stats(conn, user_id)
        db.record_activity(conn, user_id, 'level_up', {'level': int(row['level']) + 1})


def expedition(user_id: int, difficulty: str) -> Dict[str, Any]:
    diff = {
        'easy': {'chance': 0.88, 'gold': (30, 80), 'exp': (18, 35), 'cd': 1800},
        'normal': {'chance': 0.72, 'gold': (70, 150), 'exp': (35, 70), 'cd': 3600},
        'hard': {'chance': 0.56, 'gold': (120, 260), 'exp': (70, 120), 'cd': 7200},
        'nightmare': {'chance': 0.38, 'gold': (220, 420), 'exp': (120, 210), 'cd': 14400},
    }
    if difficulty not in diff:
        raise ValueError('Unknown difficulty')
    with db.get_conn() as conn:
        sec = _ready_in(conn, user_id, 'expedition')
        if sec:
            raise ValueError(f'Экспедиция недоступна ещё {sec} сек.')
        level = int(conn.execute('SELECT level FROM users WHERE id=?', (user_id,)).fetchone()['level'])
        cfg = diff[difficulty].copy()
        chance = min(0.95, cfg['chance'] + max(0, level - 1) * 0.002)
        success = random.random() <= chance
        reward = {'gold': 0, 'exp': 0, 'items': []}
        if success:
            reward['gold'] = random.randint(*cfg['gold']) + level * 2
            reward['exp'] = random.randint(*cfg['exp']) + level
            conn.execute('UPDATE users SET gold=gold+?, exp=exp+? WHERE id=?', (reward['gold'], reward['exp'], user_id))
            item_code = conn.execute(
                "SELECT item_code FROM item_defs WHERE category IN ('food','material','elixir','scroll') ORDER BY RANDOM() LIMIT 1"
            ).fetchone()['item_code']
            qty = 1 if difficulty != 'easy' else random.randint(1, 2)
            db.add_item(conn, user_id, item_code, qty)
            reward['items'].append({'item_code': item_code, 'qty': qty})
            _apply_levelups(conn, user_id)
            db.record_activity(conn, user_id, 'expedition_win', {'difficulty': difficulty, 'reward': reward})
        else:
            db.record_activity(conn, user_id, 'expedition_fail', {'difficulty': difficulty})
        _set_cd(conn, user_id, 'expedition', cfg['cd'])
        db.recalc_stats(conn, user_id)
        return {'success': success, 'chance': round(chance, 3), 'reward': reward}


def dungeon_run(user_id: int, floor: int, difficulty: str) -> Dict[str, Any]:
    if floor < 1 or floor > 15:
        raise ValueError('Доступны уровни 1-15')
    recommended = {'easy': 25, 'medium': 50, 'hard': 75}
    if difficulty not in recommended:
        raise ValueError('Сложность: easy/medium/hard')
    with db.get_conn() as conn:
        sec = _ready_in(conn, user_id, f'dungeon_{difficulty}')
        if sec:
            raise ValueError(f'Подземелье недоступно ещё {sec} сек.')
        level = int(conn.execute('SELECT level FROM users WHERE id=?', (user_id,)).fetchone()['level'])
        base = 0.18 if difficulty == 'hard' else 0.27 if difficulty == 'medium' else 0.35
        chance = base + (level - recommended[difficulty]) * 0.012 - (floor - 1) * 0.015
        chance = max(0.05, min(0.93, chance))
        success = random.random() <= chance
        reward = {'gold': 0, 'exp': 0, 'items': []}
        if success:
            reward['gold'] = 100 + floor * (30 if difficulty == 'easy' else 50 if difficulty == 'medium' else 80)
            reward['exp'] = 60 + floor * (25 if difficulty == 'easy' else 40 if difficulty == 'medium' else 65)
            conn.execute(
                'UPDATE users SET gold=gold+?, exp=exp+?, dungeon_level=MAX(dungeon_level, ?) WHERE id=?',
                (reward['gold'], reward['exp'], floor, user_id),
            )
            item_code = conn.execute(
                "SELECT item_code FROM item_defs WHERE rarity IN ('rare','epic','legendary','mythic') ORDER BY RANDOM() LIMIT 1"
            ).fetchone()['item_code']
            db.add_item(conn, user_id, item_code, 1)
            reward['items'].append({'item_code': item_code, 'qty': 1})
            _apply_levelups(conn, user_id)
            db.record_activity(conn, user_id, 'dungeon_win', {'floor': floor, 'difficulty': difficulty, 'reward': reward})
        else:
            db.record_activity(conn, user_id, 'dungeon_fail', {'floor': floor, 'difficulty': difficulty})
        _set_cd(conn, user_id, f'dungeon_{difficulty}', 3600 if difficulty == 'easy' else 7200 if difficulty == 'medium' else 10800)
        return {'success': success, 'chance': round(chance, 3), 'reward': reward}


def use_item(user_id: int, item_code: str) -> Dict[str, Any]:
    with db.get_conn() as conn:
        item = db.get_item_def(conn, item_code)
        if item['category'] == 'equipment':
            return equip_item(user_id, item_code)
        if not item['is_consumable']:
            raise ValueError('Этот предмет нельзя использовать напрямую')
        db.remove_item(conn, user_id, item_code, 1)
        message = 'Эффект применён.'
        if item['effect_kind'] == 'restore_hp':
            conn.execute('UPDATE users SET hp = MIN(max_hp, hp + ?) WHERE id=?', (item['effect_value'], user_id))
            message = f"HP восстановлено на {item['effect_value']}"
        elif item['effect_kind'] == 'restore_energy':
            conn.execute('UPDATE users SET energy = MIN(max_energy, energy + ?) WHERE id=?', (item['effect_value'], user_id))
            message = f"Энергия восстановлена на {item['effect_value']}"
        elif item['effect_kind'] == 'add_gold':
            conn.execute('UPDATE users SET gold = gold + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Получено золото: +{item['effect_value']}"
        elif item['effect_kind'] == 'add_exp':
            conn.execute('UPDATE users SET exp = exp + ? WHERE id=?', (item['effect_value'], user_id))
            _apply_levelups(conn, user_id)
            message = f"Получен опыт: +{item['effect_value']}"
        elif item['effect_kind'] == 'add_slots':
            conn.execute('UPDATE users SET inventory_slots = inventory_slots + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Лимит инвентаря увеличен на {item['effect_value']} слотов"
        elif item['effect_kind'] == 'add_weight_limit':
            conn.execute('UPDATE users SET weight_limit = weight_limit + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Лимит веса увеличен на {item['effect_value']}"
        elif item['effect_kind'] == 'buff_attack':
            conn.execute('UPDATE users SET attack = attack + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Сила атаки увеличена на {item['effect_value']}"
        elif item['effect_kind'] == 'buff_defense':
            conn.execute('UPDATE users SET defense = defense + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Защита увеличена на {item['effect_value']}"
        elif item['effect_kind'] == 'buff_speed':
            conn.execute('UPDATE users SET speed = speed + ? WHERE id=?', (item['effect_value'], user_id))
            message = f"Скорость увеличена на {item['effect_value']}"
        elif item['effect_kind'] == 'buff_hp':
            conn.execute('UPDATE users SET max_hp = max_hp + ?, hp = hp + ? WHERE id=?', (item['effect_value'], item['effect_value'], user_id))
            message = f"Максимальное HP увеличено на {item['effect_value']}"
        elif item['effect_kind'] == 'buff_energy':
            conn.execute('UPDATE users SET max_energy = max_energy + ?, energy = energy + ? WHERE id=?', (item['effect_value'], item['effect_value'], user_id))
            message = f"Максимальная энергия увеличена на {item['effect_value']}"
        db.record_activity(conn, user_id, 'item_used', {'item_code': item_code, 'effect_kind': item['effect_kind'], 'effect_value': item['effect_value']})
        return {'ok': True, 'message': message, 'user': db.get_user_with_conn(conn, user_id)}


def equip_item(user_id: int, item_code: str) -> Dict[str, Any]:
    with db.get_conn() as conn:
        item = db.get_item_def(conn, item_code)
        if item['category'] != 'equipment':
            raise ValueError('Это не экипировка')
        slot = item['equip_slot']
        old = conn.execute(
            '''SELECT i.id FROM inventory i JOIN item_defs d ON i.item_code=d.item_code
               WHERE i.user_id=? AND d.equip_slot=? AND i.equipped=1''',
            (user_id, slot),
        ).fetchone()
        if old:
            conn.execute('UPDATE inventory SET equipped=0 WHERE id=?', (old['id'],))
        row = conn.execute('SELECT id FROM inventory WHERE user_id=? AND item_code=? AND equipped=0', (user_id, item_code)).fetchone()
        if not row:
            raise ValueError('Этого предмета нет в инвентаре')
        conn.execute('UPDATE inventory SET equipped=1 WHERE id=?', (row['id'],))
        db.recalc_stats(conn, user_id)
        db.record_activity(conn, user_id, 'equipment_changed', {'item_code': item_code, 'slot': slot})
        return {'ok': True, 'message': f'Экипирован предмет: {item["name"]}', 'user': db.get_user_with_conn(conn, user_id)}


def craft_recipe(user_id: int, recipe_code: str) -> Dict[str, Any]:
    with db.get_conn() as conn:
        recipe = conn.execute('SELECT * FROM recipes WHERE recipe_code=?', (recipe_code,)).fetchone()
        if not recipe:
            raise ValueError('Рецепт не найден')
        ingredients = json.loads(recipe['ingredients_json'])
        for ing in ingredients:
            row = conn.execute('SELECT quantity FROM inventory WHERE user_id=? AND item_code=? AND equipped=0', (user_id, ing['item_code'])).fetchone()
            if not row or row['quantity'] < ing['qty']:
                raise ValueError(f'Не хватает ресурса {ing["item_code"]}')
        for ing in ingredients:
            db.remove_item(conn, user_id, ing['item_code'], ing['qty'])
        db.add_item(conn, user_id, recipe['result_item_code'], int(recipe['result_qty']))
        db.record_activity(conn, user_id, 'craft_done', {'recipe_code': recipe_code, 'result_item_code': recipe['result_item_code']})
        return {'ok': True, 'message': f'Создан предмет {recipe["result_item_code"]} x{recipe["result_qty"]}'}


def buy_shop_offer(user_id: int, offer_id: int) -> Dict[str, Any]:
    with db.get_conn() as conn:
        offer = conn.execute('SELECT * FROM shop_offers WHERE id=?', (offer_id,)).fetchone()
        if not offer:
            raise ValueError('Лот магазина не найден')
        gold = int(conn.execute('SELECT gold FROM users WHERE id=?', (user_id,)).fetchone()['gold'])
        if gold < int(offer['price']):
            raise ValueError('Недостаточно золота')
        conn.execute('UPDATE users SET gold = gold - ? WHERE id=?', (offer['price'], user_id))
        db.add_item(conn, user_id, offer['item_code'], int(offer['quantity']))
        db.record_activity(conn, user_id, 'shop_buy', {'offer_id': offer_id, 'item_code': offer['item_code'], 'price': int(offer['price'])})
        return {'ok': True, 'message': 'Покупка выполнена'}


def create_market_listing(user_id: int, item_code: str, quantity: int, price: int) -> Dict[str, Any]:
    if quantity <= 0 or price <= 0:
        raise ValueError('Количество и цена должны быть положительными')
    with db.get_conn() as conn:
        db.remove_item(conn, user_id, item_code, quantity)
        conn.execute(
            'INSERT INTO market_listings (seller_id, item_code, quantity, price, status, created_at) VALUES (?, ?, ?, ?, "open", ?)',
            (user_id, item_code, quantity, price, db.now_str()),
        )
        db.record_activity(conn, user_id, 'market_sell', {'item_code': item_code, 'quantity': quantity, 'price': price})
        return {'ok': True, 'message': 'Лот выставлен на рынок'}


def get_market() -> List[Dict[str, Any]]:
    with db.get_conn() as conn:
        rows = conn.execute(
            '''SELECT m.id, m.seller_id, u.display_name AS seller_name, m.item_code, m.quantity, m.price, m.created_at,
                      d.name, d.rarity, d.category, d.icon, d.description
               FROM market_listings m
               JOIN item_defs d ON m.item_code=d.item_code
               JOIN users u ON m.seller_id=u.id
               WHERE m.status='open'
               ORDER BY m.created_at DESC'''
        ).fetchall()
        return [dict(r) for r in rows]


def buy_market_listing(user_id: int, listing_id: int) -> Dict[str, Any]:
    with db.get_conn() as conn:
        row = conn.execute('SELECT * FROM market_listings WHERE id=? AND status="open"', (listing_id,)).fetchone()
        if not row:
            raise ValueError('Лот не найден')
        if int(row['seller_id']) == user_id:
            raise ValueError('Нельзя купить собственный лот')
        gold = int(conn.execute('SELECT gold FROM users WHERE id=?', (user_id,)).fetchone()['gold'])
        if gold < int(row['price']):
            raise ValueError('Недостаточно золота')
        conn.execute('UPDATE users SET gold = gold - ? WHERE id=?', (row['price'], user_id))
        conn.execute('UPDATE users SET gold = gold + ? WHERE id=?', (row['price'], row['seller_id']))
        db.add_item(conn, user_id, row['item_code'], int(row['quantity']))
        conn.execute('UPDATE market_listings SET status="sold" WHERE id=?', (listing_id,))
        db.record_activity(conn, user_id, 'market_buy', {'listing_id': listing_id, 'item_code': row['item_code'], 'price': int(row['price'])})
        return {'ok': True, 'message': 'Лот куплен'}


def bank_status(user_id: int) -> Dict[str, Any]:
    user = db.get_user(user_id)
    overdue = False
    if user['bank_due_at']:
        overdue = datetime.fromisoformat(user['bank_due_at']) < db.utcnow() and int(user['bank_debt']) > 0
    limit = 100 + int(user['level']) * 25
    return {
        'debt': int(user['bank_debt']),
        'due_at': user['bank_due_at'],
        'credit_limit': limit,
        'can_take_credit': int(user['bank_debt']) == 0,
        'overdue': overdue,
    }


def bank_credit(user_id: int) -> Dict[str, Any]:
    with db.get_conn() as conn:
        row = conn.execute('SELECT level, bank_debt FROM users WHERE id=?', (user_id,)).fetchone()
        if int(row['bank_debt']) > 0:
            raise ValueError('Сначала погаси активный кредит')
        amount = 100 + int(row['level']) * 25
        debt = int(amount * 1.18)
        due_at = (db.utcnow() + timedelta(days=3)).isoformat()
        conn.execute('UPDATE users SET gold = gold + ?, bank_debt=?, bank_due_at=? WHERE id=?', (amount, debt, due_at, user_id))
        db.record_activity(conn, user_id, 'bank_credit', {'amount': amount, 'debt': debt, 'due_at': due_at})
        return {'ok': True, 'message': f'Выдан кредит: {amount} золота. Вернуть нужно {debt} до {due_at}'}


def repay_bank(user_id: int, amount: int | None = None) -> Dict[str, Any]:
    with db.get_conn() as conn:
        row = conn.execute('SELECT gold, bank_debt FROM users WHERE id=?', (user_id,)).fetchone()
        debt = int(row['bank_debt'])
        if debt <= 0:
            raise ValueError('Активного кредита нет')
        pay = debt if amount is None else max(1, min(int(amount), debt))
        gold = int(row['gold'])
        if gold < pay:
            raise ValueError('Недостаточно золота для погашения')
        new_debt = debt - pay
        conn.execute(
            'UPDATE users SET gold=gold-?, bank_debt=?, bank_due_at=CASE WHEN ?=0 THEN "" ELSE bank_due_at END WHERE id=?',
            (pay, new_debt, new_debt, user_id),
        )
        db.record_activity(conn, user_id, 'bank_repay', {'amount': pay, 'left': new_debt})
        return {'ok': True, 'message': f'Погашено {pay} золота. Остаток долга: {new_debt}'}


def pvp_fight(user_id: int, opponent_user_id: int) -> Dict[str, Any]:
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM users WHERE id IN (?, ?)', (user_id, opponent_user_id)).fetchall()]
        if len(rows) != 2:
            raise ValueError('Соперник не найден')
        a = next(u for u in rows if int(u['id']) == user_id)
        b = next(u for u in rows if int(u['id']) == opponent_user_id)
        score_a = a['attack'] * 1.35 + a['defense'] * 1.1 + a['speed'] * 0.9 + a['max_hp'] * 0.12 + random.randint(-20, 20)
        score_b = b['attack'] * 1.35 + b['defense'] * 1.1 + b['speed'] * 0.9 + b['max_hp'] * 0.12 + random.randint(-20, 20)
        winner = a if score_a >= score_b else b
        loser = b if int(winner['id']) == int(a['id']) else a
        conn.execute('UPDATE users SET pvp_wins = pvp_wins + 1, gold = gold + 30, exp = exp + 25 WHERE id=?', (winner['id'],))
        conn.execute('UPDATE users SET pvp_losses = pvp_losses + 1, gold = gold + 5, exp = exp + 8 WHERE id=?', (loser['id'],))
        _apply_levelups(conn, int(winner['id']))
        _apply_levelups(conn, int(loser['id']))
        db.record_activity(conn, int(winner['id']), 'pvp_win', {'opponent_user_id': int(loser['id']), 'opponent_name': loser['display_name']})
        db.record_activity(conn, int(loser['id']), 'pvp_loss', {'opponent_user_id': int(winner['id']), 'opponent_name': winner['display_name']})
        return {'winner_user_id': winner['id'], 'winner_name': winner['display_name'], 'loser_name': loser['display_name']}


def gift_item(user_id: int, to_user_id: int, item_code: str, quantity: int) -> Dict[str, Any]:
    if user_id == to_user_id:
        raise ValueError('Нельзя отправить подарок самому себе')
    with db.get_conn() as conn:
        db.remove_item(conn, user_id, item_code, quantity)
        db.add_item(conn, to_user_id, item_code, quantity)
        db.record_activity(conn, user_id, 'gift_send', {'to_user_id': to_user_id, 'item_code': item_code, 'quantity': quantity})
        db.record_activity(conn, to_user_id, 'gift_receive', {'from_user_id': user_id, 'item_code': item_code, 'quantity': quantity})
        return {'ok': True, 'message': 'Подарок отправлен'}


def generate_link_code(user_id: int) -> Dict[str, Any]:
    return {'code': db.generate_link_code(user_id), 'expires_minutes': 15}


def bind_android_by_code(code: str) -> Dict[str, Any]:
    user_id = db.consume_link_code(code)
    if not user_id:
        raise ValueError('Код недействителен или истёк')
    token = db.create_session(user_id)
    return {'token': token, 'user': db.get_user(user_id)}


def leaderboard() -> Dict[str, Any]:
    with db.get_conn() as conn:
        boards = {}
        for key, order in [('level', 'level DESC, exp DESC'), ('pvp', 'pvp_wins DESC, level DESC'), ('gold', 'gold DESC, level DESC')]:
            rows = conn.execute(f'SELECT id, display_name, level, exp, gold, pvp_wins FROM users ORDER BY {order} LIMIT 20').fetchall()
            boards[key] = [dict(r) for r in rows]
        return boards


def activity_feed(user_id: int) -> List[Dict[str, Any]]:
    return db.get_recent_activity(user_id, limit=25)


def daily_status(user_id: int) -> Dict[str, Any]:
    today = db.start_of_day().date().isoformat()
    claim_key = f'daily:{today}'
    claimed = db.get_claim(user_id, claim_key) is not None
    streak = 0
    with db.get_conn() as conn:
        keys = set(db.list_claims_with_prefix(conn, user_id, 'daily:'))
    cur = db.start_of_day().date()
    while f'daily:{cur.isoformat()}' in keys:
        streak += 1
        cur = cur - timedelta(days=1)
    reward = {
        'gold': 120 + streak * 20,
        'exp': 50 + streak * 10,
        'item_code': 'ID401001' if streak % 2 == 0 else 'ID501001',
    }
    return {
        'claimed': claimed,
        'streak': streak,
        'today_key': today,
        'reward': reward,
        'next_reset_at': (db.start_of_day() + timedelta(days=1)).isoformat(),
    }


def claim_daily(user_id: int) -> Dict[str, Any]:
    status = daily_status(user_id)
    if status['claimed']:
        raise ValueError('Ежедневная награда уже получена сегодня')
    with db.get_conn() as conn:
        reward = status['reward']
        conn.execute('UPDATE users SET gold=gold+?, exp=exp+? WHERE id=?', (reward['gold'], reward['exp'], user_id))
        db.add_item(conn, user_id, reward['item_code'], 1)
        db.set_claim(conn, user_id, f"daily:{status['today_key']}", reward)
        _apply_levelups(conn, user_id)
        db.record_activity(conn, user_id, 'daily_claim', reward)
        return {'ok': True, 'message': f"Получено: {reward['gold']} золота, {reward['exp']} опыта и бонусный предмет"}


def _daily_quests() -> List[Dict[str, Any]]:
    today = db.start_of_day().date().isoformat()
    return [
        {'code': f'q_expedition:{today}', 'title': 'Сходи в экспедицию', 'kind': 'expedition_win', 'need': 1, 'reward_gold': 140, 'reward_exp': 60},
        {'code': f'q_craft:{today}', 'title': 'Скрафти предмет', 'kind': 'craft_done', 'need': 1, 'reward_gold': 110, 'reward_exp': 75},
        {'code': f'q_trade:{today}', 'title': 'Сделай торговое действие', 'kind_any': ['market_sell', 'market_buy'], 'need': 1, 'reward_gold': 160, 'reward_exp': 90},
    ]


def quests_status(user_id: int) -> List[Dict[str, Any]]:
    with db.get_conn() as conn:
        counters = db.get_activity_counters(conn, user_id, since=db.start_of_day())
        claims = set(db.list_claims_with_prefix(conn, user_id, 'quest:'))
    out = []
    for quest in _daily_quests():
        if 'kind_any' in quest:
            progress = sum(counters.get(kind, 0) for kind in quest['kind_any'])
        else:
            progress = counters.get(quest['kind'], 0)
        out.append({
            **quest,
            'progress': progress,
            'completed': progress >= quest['need'],
            'claimed': f"quest:{quest['code']}" in claims,
        })
    return out


def claim_quest(user_id: int, quest_code: str) -> Dict[str, Any]:
    quest = next((q for q in quests_status(user_id) if q['code'] == quest_code), None)
    if not quest:
        raise ValueError('Квест не найден')
    if quest['claimed']:
        raise ValueError('Награда за этот квест уже получена')
    if not quest['completed']:
        raise ValueError('Квест ещё не выполнен')
    with db.get_conn() as conn:
        conn.execute('UPDATE users SET gold=gold+?, exp=exp+? WHERE id=?', (quest['reward_gold'], quest['reward_exp'], user_id))
        db.set_claim(conn, user_id, f"quest:{quest_code}", {'gold': quest['reward_gold'], 'exp': quest['reward_exp']})
        _apply_levelups(conn, user_id)
        db.record_activity(conn, user_id, 'quest_claim', {'quest_code': quest_code, 'gold': quest['reward_gold'], 'exp': quest['reward_exp']})
        return {'ok': True, 'message': f"Награда получена: {quest['reward_gold']} золота и {quest['reward_exp']} опыта"}
