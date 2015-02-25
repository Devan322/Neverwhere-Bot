# Utility class to make writing skill perks easier
from Neverwherebot.perk import Perk
import Neverwherebot.models as models


class Perk(Perk):
    category = ("Skill")

    def on_add(self, character):
        char = models.Character.objects.get(name=character)
        skill = models.Skill.objects.get(name=self.name)
        if not models.CharacterSkill.filter(skill=skill.pk).filter(character=char.pk):
            new = models.CharacterSkill()
            new.skill = skill.pk
            new.character = char.pk
            new.save()

    def on_recalc(self, character):
        char = models.Character.objects.get(name=character)
        skill = models.Skill.objects.get(name=self.name)
        charskill = models.CharacterSkill.filter(skill=skill.pk).filter(character=char.pk)
        if charskill.level == 0 or charskill.level == 2:
            charskill.level += 2
        else:
            charskill.level += 1

        charskill.save()