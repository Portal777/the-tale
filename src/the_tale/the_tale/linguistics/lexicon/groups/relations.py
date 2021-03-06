# coding: utf-8

from rels import Column
from rels.django import DjangoEnum

from the_tale.linguistics.lexicon.relations import VARIABLE as V


class LEXICON_GROUP(DjangoEnum):
    index_group = Column()
    description = Column(unique=False)
    variables = Column(unique=False, no_index=True)

    records = (('ACTION_BATTLEPVE1X1', 0, 'Действие: сражение с монстром', 0,
               'Описание событий, происходящих при сражении с монстрами.',
               {V.HERO: 'герой', V.ACTOR: 'герой или монстр', V.DAMAGE: 'количество урона', V.EXPERIENCE: 'опыт', V.ARTIFACT: 'предмет', V.MOB: 'монстр', V.COMPANION: 'спутник', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_EQUIPPING', 1, 'Действие: экипировка', 10000,
               'Описание событий во время изменения экипировки героя.',
               {V.UNEQUIPPED: 'снимаемый артефакт', V.ITEM: 'артефакт', V.HERO: 'герой', V.EQUIPPED: 'экипируемый артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_EVENT', 2, 'Небольшие события', 20000,
               'Описания небольших событий во время действий героя.',
               {V.PLACE: 'город', V.COINS: 'количество монет', V.HERO: 'герой', V.EXPERIENCE: 'опыт', V.ARTIFACT: 'артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_IDLENESS', 3, 'Действие: бездействие героя', 30000,
               'Описание моментов, когда герой ничего не делает.',
               {V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_INPLACE', 4, 'Действие: посещение города', 40000,
               'Описание событий, происходящих при посещении героем города.',
               {V.HERO: 'герой', V.COINS: 'количество монет', V.ARTIFACT: 'предмет', V.SELL_PRICE: 'цена продажи', V.PERSON: 'житель', V.PLACE: 'город', V.EXPERIENCE: 'количество опыта', V.OLD_ARTIFACT: 'старый артефакт', V.COMPANION: 'спутник', V.HEALTH: 'количество здоровья', V.ENERGY: 'энергия', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_MOVENEARPLACE', 5, 'Действие: путешествие в окрестностях города', 50000,
               'Описание действий, происходящих при путешествии героя в окрестностях города.',
               {V.PLACE: 'город', V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_MOVETO', 6, 'Действие: путешествие между городами', 60000,
               'Описание событий при путешествии героя между городами (по дороге)',
               {V.DESTINATION: 'конечное место назначения', V.HERO: 'герой', V.CURRENT_DESTINATION: 'текущее место назначения', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_QUEST', 7, 'Действие: выполнение задания', 70000,
               'Герой выполняет специфические для задания действия.',
               {V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_REGENERATE_ENERGY', 8, 'Действие: восстановление энергии', 80000,
               'Описание событий во время проведения героем религиозных обрядов.',
               {V.ENERGY: 'количество энергии', V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_REST', 9, 'Действие: лечение', 90000,
               'Описание действий во время лечения героя.',
               {V.HEALTH: 'количество здоровья', V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_RESURRECT', 10, 'Действие: воскрешение героя', 100000,
               'Описание событий при воскрешении героя',
               {V.HERO: 'герой', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_TRADING', 11, 'Действие: торговля', 110000,
               'Описание действий во время торговли',
               {V.COINS: 'количество монет', V.HERO: 'герой', V.ARTIFACT: 'предмет', V.DATE: 'дата', V.TIME: 'время'}),

               ('ANGEL_ABILITY', 12, 'Способности: Хранитель', 120000,
               'Описание результата использование способностей игрока',
               {V.HERO: 'герой', V.DROPPED_ITEM: 'выкидываемый предмет', V.ENERGY: 'энергия', V.COINS: 'количество монет', V.EXPERIENCE: 'количество опыта', V.HEALTH: 'количество здоровья', V.MOB: 'монстр', V.COMPANION: 'спутник', V.DAMAGE: 'урон', V.DATE: 'дата', V.TIME: 'время'}),

               ('HERO_ABILITY', 14, 'Способности', 140000,
               'Описание применения способностей героем (или монстром)',
               {V.ATTACKER: 'атакующий', V.HEALTH: 'количество вылеченного здоровья', V.DAMAGE: 'количество урона', V.ATTACKER_DAMAGE: 'количество урона по атакующему', V.ACTOR: 'герой или монстр', V.DEFENDER: 'защищающийся', V.COMPANION: 'спутник', V.DATE: 'дата', V.TIME: 'время'}),

               ('HERO_COMMON', 15, 'Общие сообщения, относящиеся к герою', 150000,
               'Сообщение, относящиеся к герою и не вошедшие в другие модули',
               {V.HERO: 'герой', V.LEVEL: 'уровень', V.ARTIFACT: 'артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('META_ACTION_ARENA_PVP_1X1', 16, 'Действие: дуэль на арене', 160000,
               'Описание действий во время PvP дуэли на арене',
               {V.DUELIST_2: '2-ой участник дуэли', V.DUELIST_1: '1-ый участник дуэли', V.KILLER: 'победитель', V.ATTACKER: 'атакующий', V.VICTIM: 'проигравший', V.DATE: 'дата', V.TIME: 'время'}),

               ('PVP', 17, 'PvP: фразы', 170000,
               'Фразы, употребляющиеся при PvP.',
               {V.TEXT: 'любой текст', V.EFFECTIVENESS: 'изменение эффективности', V.DUELIST_2: '2-ой участник дуэли', V.DUELIST_1: '1-ый участник дуэли', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_CARAVAN', 18, 'Задание: провести караван', 180000,
               'Тексты, относящиеся к заданию.',
               {V.INITIATOR: 'житель, начинающий задание', V.HERO: 'герой', V.ANTAGONIST_POSITION: 'место продажи награбленного', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.INITIATOR_POSITION: 'место начала задания', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_COLLECT_DEBT', 19, 'Задание: чужие обязательства', 190000,
               'Тексты, относящиеся к заданию.',
               {V.INITIATOR: 'житель, начинающий задание', V.HERO: 'герой', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.INITIATOR_POSITION: 'место начала задания', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_DELIVERY', 20, 'Задание: доставить письмо', 200000,
               'Тексты, относящиеся к заданию',
               {V.INITIATOR: 'житель, начинающий задание', V.HERO: 'герой', V.ANTAGONIST_POSITION: 'место скупки краденого', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.INITIATOR_POSITION: 'место начала задания', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.ANTAGONIST: 'житель, скупающий краденое', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_HELP', 21, 'Задание: помощь', 210000,
               'Тексты, относящиеся к заданию.',
               {V.INITIATOR: 'житель, начинающий задание', V.HERO: 'герой', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.INITIATOR_POSITION: 'место начала задания', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_HELP_FRIEND', 22, 'Задание: помощь соратнику', 220000,
               'Тексты, относящиеся к заданию.',
               {V.RECEIVER_POSITION: 'место окончания задания', V.COINS: 'количество монет', V.HERO: 'герой', V.ARTIFACT: 'артефакт', V.RECEIVER: 'житель, заканчивающий задание', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_HOMETOWN', 23, 'Задание: путешествие в родной город', 230000,
               'Тексты, относящиеся к заданию.',
               {V.RECEIVER_POSITION: 'место окончания задания', V.COINS: 'количество монет', V.HERO: 'герой', V.INITIATOR_POSITION: 'место начала задания', V.ARTIFACT: 'артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_HUNT', 24, 'Задание: охота', 240000,
               'Тексты, относящиеся к заданию.',
               {V.RECEIVER_POSITION: 'место окончания задания', V.COINS: 'количество монет', V.HERO: 'герой', V.ARTIFACT: 'артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_INTERFERE_ENEMY', 25, 'Задание: навредить противнику', 250000,
               'Тексты, относящиеся к заданию.',
               {V.HERO: 'герой', V.ANTAGONIST_POSITION: 'место деятельности противника', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.RECEIVER: 'противник', V.RECEIVER_POSITION: 'место жительства противника', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_PILGRIMAGE', 26, 'Задание: паломничество в святой город', 260000,
               'Тексты, относящиеся к заданию.',
               {V.RECEIVER_POSITION: 'место окончания задания', V.COINS: 'количество монет', V.HERO: 'герой', V.INITIATOR_POSITION: 'место начала задания', V.ARTIFACT: 'артефакт', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_SEARCH_SMITH', 27, 'Задание: посещение кузнеца', 270000,
               'Тексты, относящиеся к заданию.',
               {V.UNEQUIPPED: 'снимаемый артефакт', V.HERO: 'герой', V.COINS: 'цена работы кузнеца', V.ARTIFACT: 'артефакт', V.SELL_PRICE: 'цена продажи', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.DATE: 'дата', V.TIME: 'время'}),

               ('QUEST_SPYING', 28, 'Задание: шпионаж', 280000,
               'Тексты, относящиеся к заданию.',
               {V.INITIATOR: 'житель, начинающий задание', V.HERO: 'герой', V.COINS: 'количество монет', V.ARTIFACT: 'артефакт', V.INITIATOR_POSITION: 'место начала задания', V.RECEIVER: 'житель, заканчивающий задание', V.RECEIVER_POSITION: 'место окончания задания', V.DATE: 'дата', V.TIME: 'время'}),

               ('COMPANIONS', 29, 'Спутники', 290000,
               'Тексты, относящиеся к спутникам.',
               {V.COMPANION_OWNER: 'владелец спутника', V.COMPANION: 'спутник', V.ATTACKER: 'атакущий спутника', V.COINS: 'вырученные средства', V.EXPERIENCE: 'опыт', V.HEALTH: 'количество здоровья', V.MOB: 'монстр', V.DESTINATION: 'место назначения', V.DAMAGE: 'урон', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_HEAL_COMPANION', 30, 'Действие: уход за спутником', 300000,
               'Герой ухаживает за спутником (обрабатывает раны, смазывает детальки, чистит карму, в зависимости от спутника).',
               {V.HERO: 'герой', V.COMPANION: 'спутник', V.HEALTH: 'количество здоровья', V.DATE: 'дата', V.TIME: 'время'}),

               ('JOBS', 31, 'Занятия Мастеров', 310000,
               'Названия занятий и записи в дневник героев',
               {V.HERO: 'герой', V.PERSON: 'мастер', V.PLACE: 'город', V.COINS: 'монеты', V.ARTIFACT: 'артефакт', V.EXPERIENCE: 'опыт', V.ENERGY: 'энергия', V.DATE: 'дата', V.TIME: 'время'}),

               ('ACTION_FIRST_STEPS', 32, 'Действие: первые шаги героя', 320000,
               'Герой только что завершил инициацию и осознаёт свою новую роль в мире.',
               {V.HERO: 'герой', V.PLACE: 'город', V.DATE: 'дата', V.TIME: 'время'}),

               )
