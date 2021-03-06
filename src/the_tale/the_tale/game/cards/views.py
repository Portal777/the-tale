
import uuid

from rels.django import DjangoEnum

from dext.common.utils import views as dext_views
from dext.common.utils.urls import UrlBuilder, url

from the_tale import amqp_environment

from the_tale.common.postponed_tasks.prototypes import PostponedTaskPrototype

from the_tale.common.utils import api
from the_tale.common.utils import list_filter
from the_tale.common.utils import views as utils_views
from the_tale.common.utils import exceptions as utils_exceptions

from the_tale.accounts import views as accounts_views

from the_tale.game import relations as game_relations

from the_tale.game.heroes import views as heroes_views
from the_tale.game.heroes import relations as heroes_relations
from the_tale.game.heroes import postponed_tasks as heroes_postponed_tasks

from . import relations
from . import tt_api
from . import logic
from . import cards
from . import conf


########################################
# processors definition
########################################

class AccountCardsLoader(dext_views.BaseViewProcessor):
    def preprocess(self, context):
        context.account_cards = tt_api.load_cards(context.account.id)


class AccountCardProcessor(dext_views.ArgumentProcessor):
    ERROR_MESSAGE = 'У Вас нет такой карты'
    GET_NAME = 'card'
    CONTEXT_NAME = 'account_card'

    def parse(self, context, raw_value):
        try:
            card_uid = uuid.UUID(raw_value)
        except ValueError:
            self.raise_wrong_format()

        if card_uid not in context.account_cards:
            self.raise_wrong_value()

        return context.account_cards[card_uid]


class AccountCardsProcessor(dext_views.ArgumentProcessor):
    ERROR_MESSAGE = 'У вас нет как минимум одной из указанных карт'
    POST_NAME = 'card'
    CONTEXT_NAME = 'cards'
    IN_LIST = True

    def parse(self, context, raw_value):
        try:
            cards_uids = [uuid.UUID(card_id.strip()) for card_id in raw_value]
        except ValueError:
            self.raise_wrong_format()

        for card_uid in cards_uids:
            if card_uid not in context.account_cards:
                self.raise_wrong_value()

        return [context.account_cards[card_uid] for card_uid in cards_uids]


########################################
# resource and global processors
########################################
resource = dext_views.Resource(name='cards')
resource.add_processor(accounts_views.CurrentAccountProcessor())
resource.add_processor(utils_views.FakeResourceProcessor())
resource.add_processor(heroes_views.CurrentHeroProcessor())

guide_resource = dext_views.Resource(name='cards')
guide_resource.add_processor(accounts_views.CurrentAccountProcessor())
guide_resource.add_processor(utils_views.FakeResourceProcessor())

########################################
# filters
########################################

class INDEX_ORDER(DjangoEnum):
    records = ( ('RARITY', 0, 'по редкости'),
                ('NAME', 1, 'по имени') )

CARDS_FILTER = [list_filter.reset_element(),
                list_filter.choice_element('редкость:', attribute='rarity', choices=[(None, 'все')] + list(relations.RARITY.select('value', 'text'))),
                list_filter.choice_element('доступность:', attribute='availability', choices=[(None, 'все')] + list(relations.AVAILABILITY.select('value', 'text'))),
                list_filter.choice_element('сортировка:',
                                           attribute='order_by',
                                           choices=list(INDEX_ORDER.select('value', 'text')),
                                           default_value=INDEX_ORDER.RARITY.value)]

class CardsFilter(list_filter.ListFilter):
    ELEMENTS = CARDS_FILTER



########################################
# views
########################################

@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@AccountCardProcessor()
@resource('use-dialog')
def use_dialog(context):

    favorite_items = {slot: context.account_hero.equipment.get(slot)
                      for slot in heroes_relations.EQUIPMENT_SLOT.records
                      if context.account_hero.equipment.get(slot) is not None}

    return dext_views.Page('cards/use_dialog.html',
                           content={'hero': context.account_hero,
                                    'card': context.account_card,
                                    'form': context.account_card.get_form(hero=context.account_hero),
                                    'dialog_info': context.account_card.get_dialog_info(hero=context.account_hero),
                                    'resource': context.resource,
                                    'EQUIPMENT_SLOT': heroes_relations.EQUIPMENT_SLOT,
                                    'RISK_LEVEL': heroes_relations.RISK_LEVEL,
                                    'COMPANION_DEDICATION': heroes_relations.COMPANION_DEDICATION,
                                    'COMPANION_EMPATHY': heroes_relations.COMPANION_EMPATHY,
                                    'ENERGY_REGENERATION': heroes_relations.ENERGY_REGENERATION,
                                    'ARCHETYPE': game_relations.ARCHETYPE,
                                    'favorite_items': favorite_items} )

@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@AccountCardProcessor()
@api.Processor(versions=(conf.settings.USE_API_VERSION, ))
@resource('api', 'use', name='api-use', method='POST')
def api_use(context):
    form = context.account_card.get_form(data=context.django_request.POST, hero=context.account_hero)

    if not form.is_valid():
        raise dext_views.ViewError(code='form_errors', message=form.errors)

    task = context.account_card.activate(context.account_hero, data=form.get_card_data())

    return dext_views.AjaxProcessing(task.status_url)


@accounts_views.LoginRequiredProcessor()
@api.Processor(versions=(conf.settings.GET_API_VERSION, ))
@resource('api', 'get', name='api-get', method='post')
def api_get(context):
    choose_task = heroes_postponed_tasks.GetCardTask(hero_id=context.account_hero.id)

    task = PostponedTaskPrototype.create(choose_task)

    amqp_environment.environment.workers.supervisor.cmd_logic_task(context.account.id, task.id)

    return dext_views.AjaxProcessing(task.status_url)


@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@AccountCardsProcessor()
@api.Processor(versions=(conf.settings.COMBINE_API_VERSION, ))
@resource('api', 'combine', name='api-combine', method='post')
def api_combine(context):
    card, result = logic.get_combined_card(allow_premium_cards=context.account.is_premium, combined_cards=context.cards)

    if not result.is_SUCCESS:
        raise dext_views.ViewError(code='wrong_cards', message=result.text)

    try:
        tt_api.change_cards(account_id=context.account.id,
                            operation_type='combine-cards',
                            to_add=[card],
                            to_remove=context.cards)
    except utils_exceptions.TTAPIUnexpectedAPIStatus:
        # return error, in most cases it is duplicate request
        raise dext_views.ViewError(code='can_not_combine_cards',
                                   message='Не удалось объединить карты. Попробуйте обновить страницу и повторить попытку.')

    ##################################
    # change combined cards statistics
    logic_task = heroes_postponed_tasks.InvokeHeroMethodTask(hero_id=context.account.id,
                                                             method_name='new_cards_combined',
                                                             method_kwargs={'number': 1})
    task = PostponedTaskPrototype.create(logic_task)
    amqp_environment.environment.workers.supervisor.cmd_logic_task(account_id=context.account.id, task_id=task.id)
    ##################################

    MESSAGE = '''
<p>Вы получаете новую карту: <span class="%(rarity)s-card-label">%(name)s</span><br/><br/></p>

<blockquote>%(description)s</blockquote>
'''

    message = MESSAGE % {'name': card.name[0].upper() + card.name[1:],
                         'description': card.effect.DESCRIPTION,
                         'rarity': card.type.rarity.name.lower()}

    return dext_views.AjaxOk(content={'message': message,
                                      'card': card.ui_info()})


@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@api.Processor(versions=(conf.settings.GET_CARDS_API_VERSION, ))
@resource('api', 'get-cards', name='api-get-cards', method='get')
def api_get_cards(context):
    return dext_views.AjaxOk(content={'cards': [card.ui_info() for card in context.account_cards.values()]})


@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@AccountCardsProcessor()
@api.Processor(versions=(conf.settings.MOVE_TO_STORAGE_API_VERSION, ))
@resource('api', 'move-to-storage', name='api-move-to-storage', method='post')
def api_move_to_storage(context):
    tt_api.change_cards_storage(account_id=context.account.id,
                                operation_type='move-to-storage',
                                cards=context.cards,
                                old_storage_id=conf.FAST_STORAGE,
                                new_storage_id=conf.ARCHIVE_STORAGE)

    return dext_views.AjaxOk()


@accounts_views.LoginRequiredProcessor()
@AccountCardsLoader()
@AccountCardsProcessor()
@api.Processor(versions=(conf.settings.MOVE_TO_HAND_API_VERSION, ))
@resource('api', 'move-to-hand', name='api-move-to-hand', method='post')
def api_move_to_hand(context):
    tt_api.change_cards_storage(account_id=context.account.id,
                                operation_type='move-to-storage',
                                cards=context.cards,
                                old_storage_id=conf.ARCHIVE_STORAGE,
                                new_storage_id=conf.FAST_STORAGE)

    return dext_views.AjaxOk()



@dext_views.RelationArgumentProcessor(relation=relations.RARITY, default_value=None,
                                      error_message='неверный тип редкости карты',
                                      context_name='cards_rarity', get_name='rarity')
@dext_views.RelationArgumentProcessor(relation=relations.AVAILABILITY, default_value=None,
                                      error_message='неверный тип доступности карты',
                                      context_name='cards_availability', get_name='availability')
@dext_views.RelationArgumentProcessor(relation=INDEX_ORDER, default_value=INDEX_ORDER.RARITY,
                                      error_message='неверный тип сортировки карт',
                                      context_name='cards_order_by', get_name='order_by')
@guide_resource('')
def index(context):
    from the_tale.game.cards.relations import RARITY

    all_cards = cards.CARD.records

    if context.cards_availability:
        all_cards = [card for card in all_cards if card.availability == context.cards_availability]

    if context.cards_rarity:
        all_cards = [card for card in all_cards if card.rarity == context.cards_rarity]

    if context.cards_order_by.is_RARITY:
        all_cards = sorted(all_cards, key=lambda c: (c.rarity.value, c.text))
    elif context.cards_order_by.is_NAME:
        all_cards = sorted(all_cards, key=lambda c: (c.text, c.rarity.value))

    url_builder = UrlBuilder(url('guide:cards:'), arguments={ 'rarity': context.cards_rarity.value if context.cards_rarity else None,
                                                              'availability': context.cards_availability.value if context.cards_availability else None,
                                                              'order_by': context.cards_order_by.value})

    index_filter = CardsFilter(url_builder=url_builder, values={'rarity': context.cards_rarity.value if context.cards_rarity else None,
                                                                'availability': context.cards_availability.value if context.cards_availability else None,
                                                                'order_by': context.cards_order_by.value if context.cards_order_by else None})


    return dext_views.Page('cards/index.html',
                           content={'section': 'cards',
                                    'CARDS': all_cards,
                                    'index_filter': index_filter,
                                    'CARD_RARITY': RARITY,
                                    'resource': context.resource})
