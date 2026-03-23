def format_user_profile(user: User) -> str:
    return (
        f"👤 Никнейм: {user.nickname}\n"
        f"🐾 Персонаж: {user.character}\n"
        f"❤️ HP: {user.hp}/{user.max_hp}\n"
        f"⚡ Энергия: {user.energy}/{user.max_energy}\n"
        f"🍽️ Сытость: {user.satiety}/{user.max_satiety}\n"
        f"💰 Монеты: {user.coins}\n"
        f"💎 Кристаллы: {user.crystals}\n"
        f"⭐ Уровень: {user.level}\n"
        f"Опыт: {user.experience}"
    )
