# coding: utf-8

from the_tale.game.abilities.relations import ABILITY_TYPE

from the_tale.game.postponed_tasks import ComplexChangeTask

from the_tale.game.places import storage as places_storage



class UseAbilityTask(ComplexChangeTask):
    TYPE = 'user-ability'

    def construct_processor(self):
        from the_tale.game.abilities.deck import ABILITIES
        return ABILITIES[ABILITY_TYPE(self.processor_id)]()

    @property
    def processed_data(self):
        return {'message': self.message}
