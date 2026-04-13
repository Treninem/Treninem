from . import admin_handlers, base_handlers, feedback_handlers, friends_handlers, groups_handlers, mentorship_handlers, news_handlers, premium_handlers, profile_handlers


def register_all_handlers(application) -> None:
    admin_handlers.register(application)
    profile_handlers.register(application)
    mentorship_handlers.register(application)
    news_handlers.register(application)
    premium_handlers.register(application)
    friends_handlers.register(application)
    groups_handlers.register(application)
    feedback_handlers.register(application)
    base_handlers.register(application)
