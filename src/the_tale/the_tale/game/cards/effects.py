import uuid
import math
import random

from rels import Column
from rels.django import DjangoEnum

from the_tale.amqp_environment import environment

from the_tale.common.postponed_tasks.prototypes import PostponedTaskPrototype

from the_tale.game.balance.power import Power

from the_tale.game.places import storage as places_storage
from the_tale.game.places import logic as places_logic

from the_tale.game.persons import storage as persons_storage
from the_tale.game.persons import logic as persons_logic

from the_tale.game.balance import constants as c
from the_tale.game import relations as game_relations

from the_tale.game.artifacts.storage import artifacts_storage
from the_tale.game.artifacts import relations as artifacts_relations

from the_tale.game.heroes import relations as heroes_relations

from the_tale.game.companions import relations as companions_relations
from the_tale.game.companions import storage as companions_storage
from the_tale.game.companions import logic as companions_logic

from . import postponed_tasks
from . import objects
from . import tt_api
from . import forms


class BaseEffect:
    __slots__ = ()

    FORM_TEMPLATE = 'cards/effect_form.html'

    def __init__(self):
        pass


    def get_form(self, card, hero, data):
        return forms.Empty(data)


    def activate(self, hero, card, data):
        data['hero_id'] = hero.id
        data['account_id'] = hero.account_id
        data['card'] = {'id': card.uid.hex,
                        'data': card.serialize()}

        card_task = postponed_tasks.UseCardTask(processor_id=card.type.value,
                                                hero_id=hero.id,
                                                data=data)

        task = PostponedTaskPrototype.create(card_task)

        environment.workers.supervisor.cmd_logic_task(hero.account_id, task.id)

        return task


    def use(self, *argv, **kwargs):
        raise NotImplementedError()


    def check_hero_conditions(self, hero, data):
        return tt_api.has_cards(account_id=hero.account_id, cards_ids=[uuid.UUID(data['card']['id'])])


    def hero_actions(self, hero, data):
        card = objects.Card.deserialize(uuid.UUID(data['card']['id']), data['card']['data'])

        tt_api.change_cards(account_id=hero.account_id,
                            operation_type='use-card',
                            to_remove=[card])

        hero.statistics.change_cards_used(1)


    def create_card(self, type, available_for_auction, uid=None):
        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            uid=uid if uid else uuid.uuid4())


    def name_for_card(self, card):
        return card.type.text


    def available(self, card):
        return True


    def item_full_type(self, card):
        return '{}'.format(card.type.value)


    def full_type_names(self, card_type):
        return {'{}'.format(card_type.value): card_type.text}

    def get_dialog_info(self, card, hero):
        return None


class ModificatorBase(BaseEffect):
    __slots__ = ('base', 'level')

    def __init__(self, base, level):
        self.base = base
        self.level = level

    @property
    def modificator(self):
        return self.base*c.CARDS_LEVEL_MULTIPLIERS[self.level-1]


class LevelUp(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    def __init__(self):
        pass

    DESCRIPTION = 'Герой получает новый уровень. Накопленный опыт не сбрасывается.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        task.hero.increment_level(send_message=False)
        storage.save_bundle_data(bundle_id=task.hero.actions.current_action.bundle_id)
        return task.logic_result()


class AddExperience(ModificatorBase):
    __slots__ = ()

    @property
    def DESCRIPTION(self):
        return 'Увеличивает опыт, который герой получит за выполнение текущего задания, на %(experience)d единиц.' % {'experience': self.modificator}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if not task.hero.quests.has_quests:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет задания.')

        task.hero.quests.current_quest.current_info.experience_bonus += self.modificator
        task.hero.quests.mark_updated()

        return task.logic_result()


class AddPoliticPower(ModificatorBase):
    __slots__ = ()

    @property
    def DESCRIPTION(self):
        return 'Увеличивает влияние, которое окажет герой после выполнения текущего задания, на %(power)d единиц.' % {'power': self.modificator}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if not task.hero.quests.has_quests:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет задания.')

        task.hero.quests.current_quest.current_info.power_bonus += self.modificator
        task.hero.quests.mark_updated()

        return task.logic_result()


class AddBonusEnergy(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    @property
    def DESCRIPTION(self):
        return 'Вы получаете %(energy)d единиц дополнительной энергии.' % {'energy': self.modificator}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        task.hero.add_energy_bonus(self.modificator)
        return task.logic_result()


class AddGold(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    @property
    def DESCRIPTION(self):
        return 'Герой получает %(gold)d монет.' % {'gold': self.modificator}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        from the_tale.game.heroes.relations import MONEY_SOURCE

        task.hero.change_money(MONEY_SOURCE.EARNED_FROM_HELP, self.modificator)
        return task.logic_result()


class ChangeHabit(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    @property
    def DESCRIPTION(self):
        return 'Изменяет черту героя на {} единиц в указанную в названии сторону.'.format(int(self.modificator))


    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        habit = game_relations.HABIT_TYPE(card.data['habit_id'])

        delta = card.data['direction'] * self.modificator

        old_habits = (task.hero.habit_honor.raw_value, task.hero.habit_peacefulness.raw_value)

        task.hero.change_habits(habit, delta)

        if old_habits == (task.hero.habit_honor.raw_value, task.hero.habit_peacefulness.raw_value):
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Применение карты никак не изменит черты героя.')

        return task.logic_result(message='Черта героя изменена.')

    def allowed_habits(self):
        return game_relations.HABIT_TYPE.records

    def allowed_directions(self):
        return (-1, 1)

    def create_card(self, type, available_for_auction, habit=None, direction=None, uid=None):
        if habit is None:
            habit = random.choice(self.allowed_habits())

        if direction is None:
            direction = random.choice(self.allowed_directions())

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'habit_id': habit.value,
                                  'direction': direction},
                            uid=uid if uid else uuid.uuid4())


    def _item_full_type(self, type, habit_id, direction):
        return '{}-{}-{:+d}'.format(type.value, habit_id, direction)

    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['habit_id'], card.data['direction'])


    def full_type_names(self, card_type):
        names = {}

        for direction in self.allowed_directions():
            for habit in self.allowed_habits():
                full_type = self._item_full_type(card_type, habit.value, direction)
                names[full_type] = self._name_for_card(card_type, habit.value, direction)

        return names

    def _name_for_card(self, type, habit_id, direction):
        return '{}: {} {:+d}'.format(type.text,
                                     game_relations.HABIT_TYPE(habit_id).text,
                                     int(self.modificator * direction))

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['habit_id'], card.data['direction'])




class ChangePreference(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        from . import preferences_forms

        preference = heroes_relations.PREFERENCE_TYPE(card.data['preference_id'])

        return preferences_forms.FORMS[preference](data, hero=hero)


    def get_dialog_info(self, card, hero):
        preference = heroes_relations.PREFERENCE_TYPE(card.data['preference_id'])
        return 'heroes/preferences/{}.html'.format(preference.base_name)


    @property
    def DESCRIPTION(self):
        return 'Позволяет изменить указанное в названии предпочтение героя.'


    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        preference = heroes_relations.PREFERENCE_TYPE(card.data['preference_id'])

        if not task.hero.preferences.set(preferences_type=preference, value=task.data.get('value')):
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR,
                                     message='Мы не можете изменить предпочтение героя на то же самое.')

        storage.save_bundle_data(bundle_id=task.hero.actions.current_action.bundle_id)

        return task.logic_result()


    def allowed_preferences(self):
        return heroes_relations.PREFERENCE_TYPE.records


    def create_card(self, type, available_for_auction, preference=None, uid=None):
        if preference is None:
            preference = random.choice(self.allowed_preferences())

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'preference_id': preference.value},
                            uid=uid if uid else uuid.uuid4())

    def _item_full_type(self, type, preference_id):
        return '{}-{}'.format(type.value, preference_id)


    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['preference_id'])


    def full_type_names(self, card_type):
        names = {}

        for preference in self.allowed_preferences():
            full_type = self._item_full_type(card_type, preference.value)
            names[full_type] = self._name_for_card(card_type, preference.value)

        return names


    def _name_for_card(self, type, preference_id):
        return type.text + ': ' + heroes_relations.PREFERENCE_TYPE(preference_id).text

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['preference_id'])



class ChangeAbilitiesChoices(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Изменяет список предлагаемых герою способностей (при выборе новой способности).'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if not task.hero.abilities.rechooce_choices():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Герой не может изменить выбор способностей (возможно, больше не из чего выбирать).')

        storage.save_bundle_data(bundle_id=task.hero.actions.current_action.bundle_id)

        return task.logic_result()


class ResetAbilities(BaseEffect):
    __slots__ = ()
    DESCRIPTION = 'Сбрасывает все способности героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if task.hero.abilities.is_initial_state():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Способности героя уже сброшены.')

        task.hero.abilities.reset()

        storage.save_bundle_data(bundle_id=task.hero.actions.current_action.bundle_id)

        return task.logic_result()


class ChangeItemOfExpenditure(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    @property
    def DESCRIPTION(self):
        return 'Меняет текущую цель трат героя на указанную в названии'


    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        item = heroes_relations.ITEMS_OF_EXPENDITURE(card.data['item_id'])

        if task.hero.next_spending == item:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Герой уже копит деньги на эту цель.')

        if item.is_HEAL_COMPANION and task.hero.companion is None:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет спутника, лечить некого.')

        task.hero.next_spending = item
        task.hero.quests.mark_updated()
        return task.logic_result()


    def allowed_items(self):
        return [item for item in heroes_relations.ITEMS_OF_EXPENDITURE.records
                if not item.is_USELESS and not item.is_IMPACT]


    def create_card(self, type, available_for_auction, item=None, uid=None):
        if item is None:
            item = random.choice(self.allowed_items())

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'item_id': item.value},
                            uid=uid if uid else uuid.uuid4())


    def _item_full_type(self, type, item_id):
        return '{}-{}'.format(type.value, item_id)

    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['item_id'])


    def full_type_names(self, card_type):
        names = {}

        for item in self.allowed_items():
            full_type = self._item_full_type(card_type, item.value)
            names[full_type] = self._name_for_card(card_type, item.value)

        return names


    def _name_for_card(self, type, item_id):
        return type.text + ': ' + heroes_relations.ITEMS_OF_EXPENDITURE(item_id).text

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['item_id'])


class RepairRandomArtifact(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Чинит случайный артефакт из экипировки героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        choices = [item for item in list(task.hero.equipment.values()) if item.integrity < item.max_integrity]

        if not choices:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Экипировка не нуждается в ремонте.')

        artifact = random.choice(choices)

        artifact.repair_it()

        return task.logic_result(message='Целостность артефакта %(artifact)s полностью восстановлена.' % {'artifact': artifact.html_label()})


class RepairAllArtifacts(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Чинит все артефакты из экипировки героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if not [item for item in list(task.hero.equipment.values()) if item.integrity < item.max_integrity]:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Экипировка не нуждается в ремонте.')

        for item in list(task.hero.equipment.values()):
            item.repair_it()

        return task.logic_result()


class CancelQuest(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Отменяет текущее задание героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if not task.hero.quests.has_quests:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет задания.')

        task.hero.quests.pop_quest()
        task.hero.quests.mark_updated()

        return task.logic_result()


class GetArtifact(BaseEffect):
    __slots__ = ('type',)

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    class ARTIFACT_TYPE_CHOICES(DjangoEnum):
        rarity = Column(unique=False, single_type=False)
        description = Column()

        records = (('LOOT', 0, 'лут', artifacts_relations.RARITY.NORMAL, 'Герой получает случайный бесполезный предмет.'),
                   ('COMMON', 1, 'обычные', artifacts_relations.RARITY.NORMAL, 'Герой получает случайный артефакт лучше экипированного, близкий архетипу героя.'),
                   ('RARE', 2, 'редкие', artifacts_relations.RARITY.RARE, 'Герой получает случайный редкий артефакт лучше экипированного, близкий архетипу героя.'),
                   ('EPIC', 3, 'эпические', artifacts_relations.RARITY.EPIC, 'Герой получает случайный эпический артефакт лучше экипированного, близкий архетипу героя.'))

    def __init__(self, type):
        super().__init__()
        self.type = type

    @property
    def DESCRIPTION(self):
        return self.ARTIFACT_TYPE_CHOICES(self.type).description

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        artifact_type = self.ARTIFACT_TYPE_CHOICES(self.type)

        if artifact_type.is_LOOT:
            artifact = artifacts_storage.generate_artifact_from_list(artifacts_storage.loot,
                                                                     task.hero.level,
                                                                     rarity=artifact_type.rarity)
            task.hero.put_loot(artifact, force=True)
        else:
            artifact, unequipped, sell_price = task.hero.receive_artifact(equip=False,
                                                                          better=True,
                                                                          prefered_slot=False,
                                                                          prefered_item=True,
                                                                          archetype=True,
                                                                          rarity_type=artifact_type.rarity)

        task.hero.actions.request_replane()

        return task.logic_result(message='В рюкзаке героя появился новый артефакт: %(artifact)s.' % {'artifact': artifact.html_label()})


class InstantMonsterKill(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Мгновенно убивает монстра, с которым сражается герой.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if not task.hero.actions.current_action.TYPE.is_BATTLE_PVE_1X1:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Герой ни с кем не сражается.')

        task.hero.actions.current_action.bit_mob(task.hero.actions.current_action.mob.max_health)

        return task.logic_result()



class KeepersGoods(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Place(data)

    @property
    def DESCRIPTION(self):
        return 'Создаёт в указанном городе %(goods)d «даров Хранителей». Город будет постепенно переводить их в продукцию, пока дары не кончатся.' % {'goods': self.modificator}

    def use(self, task, storage, highlevel=None, **kwargs): # pylint: disable=R0911,W0613

        place_id = task.data.get('value')

        if place_id not in places_storage.places:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Город не найден.')

        if task.step.is_LOGIC:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.HIGHLEVEL)

        elif task.step.is_HIGHLEVEL:
            place = places_storage.places[place_id]

            place.attrs.keepers_goods += self.modificator
            place.refresh_attributes()

            places_logic.save_place(place)

            places_storage.places.update_version()

            return task.logic_result()


class RepairBuilding(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Building(data)

    @property
    def DESCRIPTION(self):
        return 'Ремонтирует указанное строение на {}%. Целостность может накапливаться больше 100%.'.format(self.modificator*100)

    def use(self, task, storage, highlevel=None, **kwargs): # pylint: disable=R0911,W0613
        building_id = task.data.get('value')

        if building_id not in places_storage.buildings:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Строение не найдено.')

        if task.step.is_LOGIC:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.HIGHLEVEL)

        elif task.step.is_HIGHLEVEL:
            building = places_storage.buildings[building_id]

            building.repair(self.modificator)

            places_logic.save_building(building)

            return task.logic_result()



class AddPersonPower(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Person(data)

    @property
    def DESCRIPTION(self):
        return 'Моментально изменяет влияние Мастера на {} единиц в указанную в названии сторону. Влияние засчитывается так, как если бы герой имел Мастера в предпочтении.'.format(int(self.modificator))

    def use(self, task, storage, highlevel=None, **kwargs): # pylint: disable=R0911,W0613

        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        delta = card.data['direction'] * self.modificator

        person_id = task.data.get('value')

        if person_id not in persons_storage.persons:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Мастер не найден.')

        person = persons_storage.persons[person_id]

        if task.step.is_LOGIC:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.HIGHLEVEL)

        elif task.step.is_HIGHLEVEL:

            person.politic_power.change_power(person=person,
                                              hero_id=task.hero_id,
                                              has_in_preferences=True,
                                              power=delta)
            persons_logic.save_person(person)
            persons_storage.persons.update_version()

            return task.logic_result(message='Влияние Мастера изменено')


    def allowed_directions(self):
        return (-1, 1)

    def create_card(self, type, available_for_auction, direction=None, uid=None):
        if direction is None:
            direction = random.choice(self.allowed_directions())

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'direction': direction},
                            uid=uid if uid else uuid.uuid4())


    def _item_full_type(self, type, direction):
        return '{}-{:+d}'.format(type.value, direction)

    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['direction'])


    def full_type_names(self, card_type):
        names = {}

        for direction in self.allowed_directions():
            full_type = self._item_full_type(card_type, direction)
            names[full_type] = self._name_for_card(card_type, direction)

        return names


    def _name_for_card(self, type, direction):
        return '{}: {:+d}'.format(type.text, int(self.modificator * direction))

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['direction'])


class AddPlacePower(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Place(data)

    @property
    def DESCRIPTION(self):
        return 'Моментально изменяет влияние города на {} единиц в указанную в названии сторону. Влияние засчитывается так, как если бы герой имел город в предпочтении.'.format(int(self.modificator))


    def use(self, task, storage, highlevel=None, **kwargs): # pylint: disable=R0911,W0613

        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        delta = card.data['direction'] * self.modificator

        place_id = task.data.get('value')

        if place_id not in places_storage.places:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Город не найден.')

        if task.step.is_LOGIC:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.HIGHLEVEL)

        elif task.step.is_HIGHLEVEL:
            place = places_storage.places[place_id]

            place.politic_power.change_power(place=place,
                                             hero_id=task.hero_id,
                                             has_in_preferences=True,
                                             power=delta)

            places_logic.save_place(place)
            places_storage.places.update_version()

            return task.logic_result(message='Влияние города изменено.')


    def allowed_directions(self):
        return (-1, 1)

    def create_card(self, type, available_for_auction, direction=None, uid=None):
        if direction is None:
            direction = random.choice(self.allowed_directions())

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'direction': direction},
                            uid=uid if uid else uuid.uuid4())

    def _item_full_type(self, type, direction):
        return '{}-{:+d}'.format(type.value, direction)

    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['direction'])


    def full_type_names(self, card_type):
        names = {}

        for direction in self.allowed_directions():
            full_type = self._item_full_type(card_type, direction)
            names[full_type] = self._name_for_card(card_type, direction)

        return names


    def _name_for_card(self, type, direction):
        return '{}: {:+d}'.format(type.text, int(self.modificator * direction))

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['direction'])




class HelpPlace(ModificatorBase):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Place(data)

    @property
    def DESCRIPTION(self):
        return 'Увеличивает известность героя в городе на {0:.1f}'.format(self.modificator)

    @property
    def success_message(self):
        return 'Известность героя увеличена на {0:.1f}'.format(self.modificator)

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        place_id = task.data.get('value')

        if place_id not in places_storage.places:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Город не найден.')

        task.hero.places_history.add_place(place_id, value=self.modificator)

        storage.save_bundle_data(bundle_id=task.hero.actions.current_action.bundle_id)

        return task.logic_result(message=self.success_message)


class ShortTeleport(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Телепортирует героя до ближайшего города либо до ближайшей ключевой точки задания. Работает только во время движения по дорогам.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        if not task.hero.actions.current_action.TYPE.is_MOVE_TO:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Герой не находится в движении.')

        if not task.hero.actions.current_action.teleport_to_place(create_inplace_action=True):
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Телепортировать героя не получилось.')

        return task.logic_result()


class LongTeleport(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Телепортирует героя в конечную точку назначения либо до ближайшей ключевой точки задания. Работает только во время движения по дорогам.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if not task.hero.actions.current_action.TYPE.is_MOVE_TO:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Герой не находится в движении.')

        if not task.hero.actions.current_action.teleport_to_end():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Телепортировать героя не получилось.')

        return task.logic_result()


class ExperienceToEnergy(BaseEffect):
    __slots__ = ('conversion',)

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    def __init__(self, conversion, **kwargs):
        super().__init__(**kwargs)
        self.conversion = conversion


    @property
    def DESCRIPTION(self):
        return 'Преобразует опыт героя на текущем уровне в дополнительную энергию по курсу %(conversion)s опыта за 1 энергии.' % {'conversion': self.conversion}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if task.hero.experience == 0:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет свободного опыта.')

        energy = task.hero.convert_experience_to_energy(self.conversion)

        return task.logic_result(message='Герой потерял весь накопленный опыт. Вы получили %(energy)d энергии.' % {'energy': energy})


class SharpRandomArtifact(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Улучшает случайный артефакт из экипировки героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        artifact = random.choice(list(task.hero.equipment.values()))

        distribution=task.hero.preferences.archetype.power_distribution
        min_power, max_power = Power.artifact_power_interval(distribution, task.hero.level)

        artifact.sharp(distribution=distribution,
                       max_power=max_power,
                       force=True)

        return task.logic_result(message='Улучшена экипировка героя: %(artifact)s.' % {'artifact': artifact.html_label()})



class SharpAllArtifacts(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Улучшает все артефакты из экипировки героя.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        for artifact in list(task.hero.equipment.values()):
            distribution=task.hero.preferences.archetype.power_distribution
            min_power, max_power = Power.artifact_power_interval(distribution, task.hero.level)

            artifact.sharp(distribution=distribution,
                           max_power=max_power,
                           force=True)

        return task.logic_result(message='Вся экипировка героя улучшена.')


class GetCompanion(BaseEffect):
    __slots__ = ('rarity',)

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    def __init__(self, rarity, **kwargs):
        super().__init__(**kwargs)
        self.rarity = rarity

    @property
    def DESCRIPTION(self):
        return 'Герой получает спутника, указанного в названии карты. Если у героя уже есть спутник, он покинет героя.'


    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        companion = companions_logic.create_companion(companions_storage.companions[card.data['companion_id']])

        task.hero.set_companion(companion)

        return task.logic_result(message='Поздравляем! Ваш герой получил нового спутника.')


    def get_available_companions(self):
        available_companions = [companion
                                for companion in companions_storage.companions.enabled_companions()
                                if companion.rarity == self.rarity and companion.mode.is_AUTOMATIC]
        return available_companions


    def create_card(self, type, available_for_auction, companion=None, uid=None):
        if companion is None:
            available_companions = self.get_available_companions()
            companion = random.choice(available_companions)

        return objects.Card(type=type,
                            available_for_auction=available_for_auction,
                            data={'companion_id': companion.id},
                            uid=uid if uid else uuid.uuid4())

    def _item_full_type(self, type, companion_id):
        return '{}-{}'.format(type.value, companion_id)


    def item_full_type(self, card):
        return self._item_full_type(card.type, card.data['companion_id'])


    def full_type_names(self, card_type):
        names = {}

        # do not skip manual companions, since can be cards with them too
        for companion in companions_storage.companions.enabled_companions():
            if companion.rarity != self.rarity:
                continue

            full_type = self._item_full_type(card_type, companion.id)
            names[full_type] = self._name_for_card(card_type, companion.id)

        return names


    def available(self, card):
        return bool(self.get_available_companions())


    def _name_for_card(self, type, companion_id):
        return type.text + ': ' + companions_storage.companions[companion_id].name

    def name_for_card(self, card):
        return self._name_for_card(card.type, card.data['companion_id'])


class ReleaseCompanion(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Спутник героя навсегда покидает его.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if task.hero.companion is None:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя сейчас нет спутника.')

        task.hero.add_message('companions_left', diary=True, companion_owner=task.hero, companion=task.hero.companion)
        task.hero.remove_companion()

        return task.logic_result(message='Поздравляем! Ваш герой получил нового спутника.')


class FreezeCompanion(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Вы получаете карту призыва текущего спутника вашего героя. Спутник покидает героя. Слаженность спутника в карте не сохраняется. Возможность продать новую карту определяется возможностью продать текущую.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613
        from . import cards

        if task.hero.companion is None:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя сейчас нет спутника.')

        if not task.hero.companion.record.abilities.can_be_freezed():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Текущий спутник не может вернуться в карту.')

        CARDS_BY_RARITIES = {companions_relations.RARITY.COMMON: cards.CARD.GET_COMPANION_COMMON,
                             companions_relations.RARITY.UNCOMMON: cards.CARD.GET_COMPANION_UNCOMMON,
                             companions_relations.RARITY.RARE: cards.CARD.GET_COMPANION_RARE,
                             companions_relations.RARITY.EPIC: cards.CARD.GET_COMPANION_EPIC,
                             companions_relations.RARITY.LEGENDARY: cards.CARD.GET_COMPANION_LEGENDARY}

        card_type = CARDS_BY_RARITIES[task.hero.companion.record.rarity]

        used_card = objects.Card.deserialize(uuid.UUID(task.data['card']['id']), task.data['card']['data'])

        card = card_type.effect.create_card(type=card_type,
                                            available_for_auction=used_card.available_for_auction,
                                            companion=task.hero.companion.record)

        task.hero.add_message('companions_left', diary=True, companion_owner=task.hero, companion=task.hero.companion)
        task.hero.remove_companion()

        tt_api.change_cards(account_id=task.hero.account_id,
                            operation_type='freeze-companion',
                            to_add=[card])

        return task.logic_result(message='Спутник покинул героя, вы получили карту спутника.')


class HealCompanion(ModificatorBase):
    __slots__ = ()

    @property
    def modificator(self):
        return int(math.ceil(super().modificator))

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    @property
    def DESCRIPTION(self):
        return 'Восстанавливает спутнику %(health)d здоровья.' % {'health': self.modificator}

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        if task.hero.companion is None:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет спутника.')

        if task.hero.companion.health == task.hero.companion.max_health:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Спутник героя полностью здоров.')

        health = task.hero.companion.heal(self.modificator)

        return task.logic_result(message='Спутник вылечен на %(health)s HP.' % {'health': health})


class UpgradeArtifact(BaseEffect):
    __slots__ = ()

    def get_form(self, card, hero, data):
        return forms.Empty(data)

    DESCRIPTION = 'Заменяет случайный экипированный не эпический артефакт, на более редкий того же вида. Параметры нового артефакта могут быть ниже параметров старого.'

    def use(self, task, storage, **kwargs): # pylint: disable=R0911,W0613

        artifacts = [artifact for artifact in list(task.hero.equipment.values()) if not artifact.rarity.is_EPIC]

        if not artifacts:
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='У героя нет экипированных не эпических артефактов.')

        artifact = random.choice(artifacts)

        task.hero.increment_equipment_rarity(artifact)

        return task.logic_result(message='Качество артефакта %(artifact)s улучшено.' % {'artifact': artifact.html_label()})


class CreateClan(BaseEffect):
    __slots__ = ()

    FORM_TEMPLATE = 'cards/effect_form_create_clan.html'

    def get_form(self, card, hero, data):
        return forms.CreateClan(data)

    DESCRIPTION = 'Создаёт новую гильдию и делает игрока её лидером.'

    def use(self, task, storage, highlevel=None, **kwargs): # pylint: disable=R0911,W0613
        from the_tale.accounts import prototypes as accounts_prototypes
        from the_tale.accounts.clans import models as clans_models
        from the_tale.accounts.clans import prototypes as clans_prototypes

        name = task.data.get('name')
        abbr = task.data.get('abbr')

        if clans_models.Membership.objects.filter(account=task.hero_id).exists():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Вы уже состоите в гильдии.')

        if clans_models.Clan.objects.filter(name=name).exists():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Гильдия с таким названием уже существует.')

        if clans_models.Clan.objects.filter(abbr=abbr).exists():
            return task.logic_result(next_step=postponed_tasks.UseCardTask.STEP.ERROR, message='Гильдия с такой аббревиатурой уже существует.')

        clans_prototypes.ClanPrototype.create(owner=accounts_prototypes.AccountPrototype.get_by_id(task.hero_id),
                                              abbr=abbr,
                                              name=name,
                                              motto='Veni, vidi, vici!',
                                              description='')

        return task.logic_result(message='Поздравляем, гильдмастер! Ваша гильдия ждёт Вас! Задайте девиз и описание гильдии на её странице.')
