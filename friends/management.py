from django.conf import settings
from django.db.models.signals import post_syncdb
import models
#from django.contrib.auth.models import User
import signals


post_syncdb.connect(
    signals.create_friendship_instance_post_syncdb,
    sender=models,
    dispatch_uid='friends.signals.create_friendship_instance_post_syncdb',
)
post_syncdb.connect(
    signals.create_userblock_instance_post_syncdb,
    sender=models,
    dispatch_uid='friends.signals.create_userblock_instance_post_syncdb',
)

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("friendship_requested", _("Friendship Requested"), _("you have received a friend request"), default=2)
        notification.create_notice_type("friendship_accepted", _("Friendship Accepted"), _("your friend request was accepted"), default=2)

    post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"
