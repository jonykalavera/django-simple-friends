"""
.. autoclass:: FriendshipRequest
    :members:

.. autoclass:: FriendshipManager
    :members:

.. autoclass:: Friendship
    :members:

.. autoclass:: UserBlocks
    :members:
"""


import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
import signals

try:
    from notification import models as notification
except:
    notification = None


class FriendshipRequest(models.Model):
    from_user = models.ForeignKey(User, related_name="invitations_from")
    to_user = models.ForeignKey(User, related_name="invitations_to")
    message = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(default=datetime.datetime.now,
                                   editable=False)
    accepted = models.BooleanField(default=False)

    class Meta:
        verbose_name = _(u'friendship request')
        verbose_name_plural = _(u'friendship requests')
        unique_together = (('to_user', 'from_user'),)

    def __unicode__(self):
        return _(u'%(from_user)s wants to be friends with %(to_user)s') % \
                    {'from_user': unicode(self.from_user),
                     'to_user': unicode(self.to_user)}

    def accept(self):
        Friendship.objects.befriend(self.from_user, self.to_user)
        self.accepted = True
        self.save()
        signals.friendship_accepted.send(sender=FriendshipRequest, friendship=self)

    def decline(self):
        signals.friendship_declined.send(sender=self)
        self.delete()

    def cancel(self):
        signals.friendship_cancelled.send(sender=self)
        self.delete()


def friendship_requested_notification(sender, friendship, **kwargs):
    if notification:
        notification.send([friendship.to_user], 
            "friendship_requested", {'friend_request': friendship,})
            
signals.friendship_requested.connect(friendship_requested_notification)

def friendship_accepted_notification(sender, friendship, **kwargs):
    if notification:
        notification.send([friendship.from_user], 
            "friendship_accepted", {'friend_request': friendship,})
            
signals.friendship_accepted.connect(friendship_accepted_notification)




class FriendshipManager(models.Manager):
    def friends_of(self, user, shuffle=False):
        qs = User.objects.filter(friendship__friends__user=user)
        if shuffle:
            qs = qs.order_by('?')
        return qs

    def are_friends(self, user1, user2):
        try:
            are_friends=bool(Friendship.objects.get(user=user1).friends.filter(
                user=user2).exists())
        except Friendship.DoesNotExist:
            are_friends=False
        return are_friends

    def befriend(self, user1, user2):
        user1_friendship, fu1_created = Friendship.objects.get_or_create(user=user1)
        user2_friendship, fu2_created = Friendship.objects.get_or_create(user=user2)
        user1_friendship.friends.add(user2_friendship)
        # Now that user1 accepted user2's friend request we should delete any
        # request by user1 to user2 so that we don't have ambiguous data
        FriendshipRequest.objects.filter(models.Q(from_user=user1,
            to_user=user2)|models.Q(to_user=user1, from_user=user2)).delete()

    def unfriend(self, user1, user2):
        # Break friendship link between users
        Friendship.objects.get(user=user1).friends.remove(
                                           Friendship.objects.get(user=user2))
        # Delete FriendshipRequest's as well
        FriendshipRequest.objects.filter(models.Q(from_user=user1,
            to_user=user2)|models.Q(to_user=user1, from_user=user2)).delete()


class Friendship(models.Model):
    user = models.OneToOneField(User, related_name='friendship')
    friends = models.ManyToManyField('self', symmetrical=True)

    objects = FriendshipManager()

    class Meta:
        verbose_name = _(u'friendship')
        verbose_name_plural = _(u'friendships')

    def __unicode__(self):
        return _(u'%(user)s\'s friends') % {'user': unicode(self.user)}

    def friend_count(self):
        return self.friends.count()
    friend_count.short_description = _(u'Friends count')

    def friend_summary(self, count=7):
        friend_list = self.friends.all().select_related(depth=1)[:count]
        return u'[%s%s]' % (u', '.join(unicode(f.user) for f in friend_list),
                            u', ...' if self.friend_count() > count else u'')
    friend_summary.short_description = _(u'Summary of friends')


class UserBlocks(models.Model):
    user = models.OneToOneField(User, related_name='user_blocks')
    blocks = models.ManyToManyField(User, related_name='blocked_by_set')

    class Meta:
        verbose_name = verbose_name_plural = _(u'user blocks')

    def __unicode__(self):
        return _(u'Users blocked by %(user)s') % {'user': unicode(self.user)}

    def block_count(self):
        return self.blocks.count()
    block_count.short_description = _(u'Blocks count')

    def block_summary(self, count=7):
        block_list = self.blocks.all()[:count]
        return u'[%s%s]' % (u', '.join(unicode(user) for user in block_list),
                            u', ...' if self.block_count() > count else u'')
    block_summary.short_description = _(u'Summary of blocks')


# Signal connections
models.signals.post_save.connect(signals.create_friendship_instance,
                                 sender=User,
                                 dispatch_uid='friends.signals.create_' \
                                              'friendship_instance')
models.signals.post_save.connect(signals.create_userblocks_instance,
                                 sender=User,
                                 dispatch_uid='friends.signals.create_' \
                                              'userblocks_instance')
