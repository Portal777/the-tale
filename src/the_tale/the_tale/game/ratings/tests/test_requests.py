
from django.core.urlresolvers import reverse

from the_tale.common.utils.testcase import TestCase

from the_tale.game.logic import create_test_map

from the_tale.game.ratings.models import RatingValues, RatingPlaces
from the_tale.game.ratings.views import RATING_TYPE


class RequestsTests(TestCase):

    def setUp(self):
        super(RequestsTests, self).setUp()
        self.place1, self.place2, self.place3 = create_test_map()

        self.account1 = self.accounts_factory.create_account()
        self.account2 = self.accounts_factory.create_account()
        self.account3 = self.accounts_factory.create_account()
        self.account4 = self.accounts_factory.create_account(is_fast=True)

        RatingValues.objects.create(account=self.account1._model, might=9, bills_count=8, magic_power=0, physic_power=0, level=9, phrases_count=0, pvp_battles_1x1_number=10, pvp_battles_1x1_victories=1, referrals_number=0, help_count=3, achievements_points=0, politics_power=1)
        RatingValues.objects.create(account=self.account2._model, might=8, bills_count=0, magic_power=9, physic_power=9, level=1, phrases_count=1, pvp_battles_1x1_number=12, pvp_battles_1x1_victories=2, referrals_number=2, help_count=0, achievements_points=3, politics_power=2)
        RatingValues.objects.create(account=self.account3._model, might=0, bills_count=9, magic_power=9, physic_power=9, level=8, phrases_count=0, pvp_battles_1x1_number=13, pvp_battles_1x1_victories=3, referrals_number=1, help_count=1, achievements_points=100, politics_power=3)

        RatingPlaces.objects.create(account=self.account1._model, might_place=1, bills_count_place=2, magic_power_place=3, physic_power_place=3, level_place=1, phrases_count_place=2, pvp_battles_1x1_number_place=2, pvp_battles_1x1_victories_place=1, referrals_number_place=3, help_count_place=1, achievements_points_place=3, politics_power_place=3)
        RatingPlaces.objects.create(account=self.account2._model, might_place=2, bills_count_place=3, magic_power_place=2, physic_power_place=2, level_place=3, phrases_count_place=1, pvp_battles_1x1_number_place=3, pvp_battles_1x1_victories_place=2, referrals_number_place=1, help_count_place=3, achievements_points_place=2, politics_power_place=2)
        RatingPlaces.objects.create(account=self.account3._model, might_place=3, bills_count_place=1, magic_power_place=1, physic_power_place=1, level_place=2, phrases_count_place=3, pvp_battles_1x1_number_place=1, pvp_battles_1x1_victories_place=3, referrals_number_place=2, help_count_place=2, achievements_points_place=1, politics_power_place=1)


    def test_index(self):
        self.check_redirect(reverse('game:ratings:'), reverse('game:ratings:show', args=[RATING_TYPE.MIGHT.value]))

    def get_show_texts(self, test_user_1, test_user_2, test_user_3, test_user_4):
        return [ (self.account1.nick, test_user_1),
                 (self.account2.nick, test_user_2),
                 (self.account3.nick, test_user_3),
                 (self.account4.nick, test_user_4)]

    def test_show(self):
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.MIGHT.value])), texts=self.get_show_texts(1, 1, 0, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.BILLS.value])), texts=self.get_show_texts(1, 0, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.MAGIC_POWER.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.PHYSIC_POWER.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.LEVEL.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.PHRASES.value])), texts=self.get_show_texts(0, 1, 0, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.PVP_BATTLES_1x1_NUMBER.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.PVP_BATTLES_1x1_VICTORIES.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.REFERRALS_NUMBER.value])), texts=self.get_show_texts(0, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.ACHIEVEMENTS_POINTS.value])), texts=self.get_show_texts(0, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.HELP_COUNT.value])), texts=self.get_show_texts(1, 1, 1, 0))
        self.check_html_ok(self.client.get(reverse('game:ratings:show', args=[RATING_TYPE.POLITICS_POWER.value])), texts=self.get_show_texts(1, 1, 1, 0))
