# coding: utf-8

import random

from the_tale.game.balance.power import Power

from the_tale.game.artifacts.storage import artifacts_storage
from the_tale.game.cards import objects as cards_objects


class ShopAccessorsMixin(object):
    __slots__ = ()

    def purchase_energy_bonus(self, energy):
        self.add_energy_bonus(energy)

    def purchase_experience(self, experience):
        self.add_experience(experience)

    def purchase_artifact(self, rarity, better):
        distribution = self.preferences.archetype.power_distribution

        power = Power.better_artifact_power_randomized(distribution, self.level) if better else Power.artifact_power_randomized(distribution, self.level)

        artifacts_storage.sync()

        artifact = random.choice(artifacts_storage.artifacts).create_artifact(level=self.level,
                                                                              power=power,
                                                                              rarity=rarity)
        self.put_loot(artifact, force=True)

        self.actions.request_replane()

        return artifact
