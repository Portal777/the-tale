# coding: utf-8

from dext.common.utils.urls import url

from the_tale.common.utils import testcase

from the_tale.game.logic import create_test_map

from the_tale.accounts.logic import get_system_user

from the_tale.accounts.friends.models import Friendship
from the_tale.accounts.friends.prototypes import FriendshipPrototype


from the_tale.accounts.clans.prototypes import ClanPrototype
from the_tale.accounts.clans.conf import clans_settings

from the_tale.forum.prototypes import CategoryPrototype



class FriendshipRequestsTests(testcase.TestCase):

    def setUp(self):
        super(FriendshipRequestsTests, self).setUp()
        create_test_map()

        self.account_1 = self.accounts_factory.create_account()
        self.account_2 = self.accounts_factory.create_account()
        self.account_3 = self.accounts_factory.create_account()

        CategoryPrototype.create(caption='category-1', slug=clans_settings.FORUM_CATEGORY_SLUG, order=0)

        self.clan_2 = ClanPrototype.create(self.account_2, abbr='abbr2', name='name2', motto='motto', description='description')
        self.clan_3 = ClanPrototype.create(self.account_3, abbr='abbr3', name='name3', motto='motto', description='description')

        self.request_login(self.account_1.email)

    def test_index__no_friends(self):
        self.check_html_ok(self.request_html(url('accounts:friends:')), texts=['pgf-no-friends-message'])

    def test_index(self):
        FriendshipPrototype.request_friendship(self.account_1, self.account_2, 'text 1')._confirm()
        FriendshipPrototype.request_friendship(self.account_1, self.account_3, 'text 2')._confirm()
        self.check_html_ok(self.request_html(url('accounts:friends:')), texts=[('pgf-no-friends-message', 0),
                                                                             (self.account_2.nick, 1),
                                                                             (self.account_3.nick, 1),
                                                                             (self.clan_2.abbr, 1),
                                                                             (self.clan_3.abbr, 1)])

    def test_candidates__friends_only(self):
        FriendshipPrototype.request_friendship(self.account_1, self.account_2, 'text 1')._confirm()
        FriendshipPrototype.request_friendship(self.account_1, self.account_3, 'text 2')._confirm()
        self.check_html_ok(self.request_html(url('accounts:friends:candidates')), texts=[('pgf-no-candidates-message', 1),
                                                                                       (self.account_2.nick, 0),
                                                                                       (self.account_3.nick, 0),
                                                                                       (self.clan_2.abbr, 0),
                                                                                       (self.clan_3.abbr, 0)])

    def test_candidates__no_candidates(self):
        self.check_html_ok(self.request_html(url('accounts:friends:candidates')), texts=['pgf-no-candidates-message'])

    def test_candidates(self):
        FriendshipPrototype.request_friendship(self.account_1, self.account_2, 'text 1')
        FriendshipPrototype.request_friendship(self.account_3, self.account_1, 'text 2')
        self.check_html_ok(self.request_html(url('accounts:friends:candidates')), texts=[('pgf-no-candidates-message', 0),
                                                                                       (self.account_2.nick, 0),
                                                                                       (self.account_3.nick, 1),
                                                                                       (self.clan_2.abbr, 0),
                                                                                       (self.clan_3.abbr, 1)])

    def test_friends__candidates_only(self):
        FriendshipPrototype.request_friendship(self.account_1, self.account_2, 'text 1')
        FriendshipPrototype.request_friendship(self.account_1, self.account_3, 'text 2')
        self.check_html_ok(self.request_html(url('accounts:friends:')), texts=[('pgf-no-friends-message', 1),
                                                                             (self.account_2.nick, 0),
                                                                             (self.account_3.nick, 0),
                                                                             (self.clan_2.abbr, 0),
                                                                             (self.clan_3.abbr, 0)])

    def test_request_dialog(self):
        self.check_html_ok(self.request_html(url('accounts:friends:request', friend=self.account_2.id)))

    def test_request_dialog__system_user(self):
        self.check_html_ok(self.request_html(url('accounts:friends:request', friend=get_system_user().id)),
                           texts=['friends.request_dialog.system_user'])

    def test_request_friendship_form_error(self):
        self.check_ajax_error(self.client.post(url('accounts:friends:request', friend=self.account_2.id), {}),
                              'friends.request_friendship.form_errors')
        self.assertEqual(Friendship.objects.all().count(), 0)

    def test_request_friendship(self):
        self.check_ajax_ok(self.client.post(url('accounts:friends:request', friend=self.account_2.id), {'text': 'text 1'}))
        self.assertEqual(Friendship.objects.all().count(), 1)
        self.assertFalse(Friendship.objects.all()[0].is_confirmed)

    def test_request_friendship_system_user(self):
        self.check_ajax_error(self.client.post(url('accounts:friends:request', friend=get_system_user().id), {'text': 'text 1'}),
                              'friends.request_friendship.system_user')
        self.assertEqual(Friendship.objects.all().count(), 0)

    def test_request_friendship__fast_friend(self):
        self.account_2.is_fast = True
        self.account_2.save()

        self.check_ajax_error(self.client.post(url('accounts:friends:request', friend=self.account_2.id), {'text': 'text 1'}),
                              'friends.request_friendship.fast_friend')
        self.assertEqual(Friendship.objects.all().count(), 0)

    def test_remove_friendship(self):
        FriendshipPrototype.request_friendship(self.account_1, self.account_2, 'text 1')._confirm()
        self.check_ajax_ok(self.client.post(url('accounts:friends:remove', friend=self.account_2.id)))
        self.assertEqual(Friendship.objects.all().count(), 0)
