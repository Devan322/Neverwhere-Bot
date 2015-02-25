# Interface.py
# Provides access to all core game world functionalities to external programs. Does NOT check any form of authentication

import imp
import os
import math

os.environ["DJANGO_SETTINGS_MODULE"] = "Neverwhere.settings"

import django
django.setup()

from slugify import slugify
import Neverwherebot.update as update
import Neverwherebot.models as model


def is_user(nick):
    if model.Player.objects.filter(nick=nick).exists():
        return True
    return False


def send_message(sender, receiver, content, flags=""):
    return update.send_message(sender, receiver, content, flags)


def get_messages(nick):
    ret = []
    try:
        p = model.Player.objects.get(nick=nick)
    except:
        return "Invalid player."

    me = model.Message.objects.filter(receiver=p)
    if not me.exists():
        return "No messages for user %s." % nick
    else:
        for m in me:
            ret.append((m.sender.nick, m.flags, str(m.sent_time), m.read, m.message))
    return ret


def register(nick, pw=None, email=None):
    # Registers the given nick
    if model.Player.objects.filter(nick=nick):
        return "Player with this nick already exists."
    new = model.Player()
    new.nick = nick
    if pw:
        new.password = pw
    if email:
        new.email = email
    new.save()
    return True


def deregister(nick):
    pass


def create_character(player, name, sex, str, dex, int, vit):
    if model.Character.objects.filter(name=name).exists():
        return "Character with this name already exists."
    if not sex == "m" and not sex == "f":
        return "Invalid sex. Please use 'm' or 'f'."
    try:
        pl = model.Player.objects.get(nick=player)
    except:
        return "Invalid player."
    new = model.Character()
    new.player = pl
    new.name = name
    new.sex = sex
    new.str = str
    new.dex = dex
    new.int = int
    new.vit = vit
    new.current_HP = new.str
    new.current_FP = new.vit
    new.current_san = 100 + (new.int-10) * 10
    new.save()
    inv = model.Storage(owner=new)
    inv.name = name + "-Inventory"
    inv.size = new.str
    inv.inventory = True
    inv.save()
    new.inventory = inv
    new.save()
    recalculate_char(name)
    return True


def delete_character(name):
    character = model.Character.objects.filter(name=name)
    if not character:
        return "Character not found."
    if character.deleted:
        return "Character is already deleted."
    character.deleted = True
    character.save()


def add_perk(perk, character):
    s = recalculate_char(character)
    if isinstance(s, basestring):
        return s

    game = model.Game.objects.filter(id=0)
    char = model.Character.objects.filter(name=character)
    if not char:
        return "Character not found."
    if not game:
        return "Game rules not found. This is a severe misconfiguration, please inform the Over GM of this bug."
    if perk.isdigits:
        p = model.Perk.objects.filter(pk=perk)
    else:
        p = model.Perk.objects.filter(name=perk)
    if not p:
        return "Perk not found."
    perks = update.get_current_day() / game.interval
    num = len(model.CharacterPerk.objects.filter(character=char))
    if num >= perks:
        return "No free perk slots available."

    f = os.path.join(os.path.abspath(__file__), 'scripts', 'perks', slugify(p.name) + ".py")
    if os.path.isfile(f):
        try:
            mod = imp.load_source(f[:-3], f)
            try:
                can_take = mod.Perk.prerequisites()
            except:
                print("Failed to find module for perk %s." % p.name)
                return False
        except:
            print("Failed to import module %s." % f)
            return False
    else:
        return False

    if not can_take:
        return "Character does not fulfill the prerequisites for this perk."

    if "Tiered" in p.category:
        count = 0
        latest = 0
        for cp in model.CharacterPerk.objects.filter(character=char):
            if cp.perk == p.pk:
                count += 1
                if cp.slot > latest:
                    latest = cp.slot
        if num + 1 > latest + count or count == 0:
            pass
        else:
            return "Character cannot take this perk at this moment due to Tiered restriction. The earliest they can take" \
                   " it is in %i perks." % (latest + count + 1) - (num + 1)

    if not mod.Perk.on_add(character):
        return "Error in 'on_add' function."
    new = model.CharacterPerk()
    new.character = char.pk
    new.perk = p.pk
    new.slot = num + 1
    new.save()
    s = recalculate_char(character)
    if isinstance(s, basestring):
        return s
    return True


def recalculate_char(character):
    try:
        char = model.Character.objects.get(name=character)
    except:
        return "Character not found."
    if char.deleted:
        return "This character has been deleted."
    try:
        inv = model.Storage.objects.get(name=char.name + "-Inventory")
    except:
        return "Inventory not found, ya dun goofd."
    old_hp = char.hp
    old_fp = char.fp
    old_san = char.san
    char.hp = char.str
    char.fp = char.vit
    char.will = char.int - 10
    char.san = 100 + (char.will * 10)
    char.mab = char.str - 10
    char.rab = char.dex - 10
    char.re = float((char.dex + char.vit) / 2)
    char.ac = 10 + math.ceil(char.re)
    char.fort = char.vit - 10
    char.per = char.int - 10
    char.mo = 4 + (char.re * 2)
    char.bl = (char.str**2)/10
    char.save()
    inv.size = 0
    inv.save()
    for cs in model.CharacterSkill.objects.filter(character=char):
        cs.level = 0
        cs.save()
    for n in range(len(model.CharacterPerk.objects.filter(character=char))):
        p = model.Perk.filter(pk=model.CharacterPerk.objects.filter(character=char).filter(slot=n).perk)
        f = os.path.join(os.path.abspath(__file__), 'scripts', 'perks', slugify(p.name) + ".py")
        if os.path.isfile(f):
            try:
                mod = imp.load_source(f[:-3], f)
                try:
                    if not mod.Perk.on_recalc(character):
                        return "Error in on_recalc()."
                except:
                    return "Failed to find module for perk %s." % p.name
            except:
                return "Failed to import module %s." % f
        else:
            return "Could not find perk script ." % f
    char = model.Character.objects.get(name=character)
    inv = model.Storage.objects.get(name=char.name + "-Inventory")
    if old_hp != char.hp:
        char.current_hp += char.current_hp - old_hp
    if old_fp != char.fp:
        char.current_fp += char.current_fp - old_fp
    if old_san != char.san:
        char.current_san += char.current_san - old_san
    char.save()
    inv.size += math.ceil(char.bl)
    inv.save()
    return True




def add_item(item, storage, amount, description=None, unit=None, weight=None):
    pass


def remove_item(item, storage, amount, unit=None, weight=None):
    pass


def get_character(character, player):
    try:
        char = model.Character.objects.get(name=character)
    except:
        return "Character not found."
    if char.player != player:
        return "You do not own this character."
    s = recalculate_char(char.name)
    if isinstance(s, basestring):
        return s
    ret = {}
    ret["sex"] = char.sex
    ret["str"] = char.str
    ret["dex"] = char.dex
    ret["int"] = char.int
    ret["vit"] = char.vit
    ret["hp"] = char.hp
    ret["fp"] = char.fp
    ret["will"] = char.will
    ret["san"] = char.san
    ret["mab"] = char.mab
    ret["rab"] = char.rab
    ret["ac"] = char.ac
    ret["re"] = char.re
    ret["fort"] = char.fort
    ret["per"] = char.per
    ret["mo"] = char.mo
    ret["bl"] = char.bl
    ret["current_hp"] = char.current_hp
    ret["current_fp"] = char.current_fp
    ret["current_san"] = char.current_san
    perks = {}
    for cp in model.CharacterPerk.objects.filter(character=char.pk):
        perks[cp.slot] = model.Perk.objects.get(pk=cp.perk).name
    ret["perks"] = perks
    skills = {}
    for cs in model.CharacterSkill.objects.filter(character=char.pk):
        skills[model.Skill.objects.get(pk=cs.skill).name] = update.get_skill(character, model.Skill.objects.get(pk=cs.skill).name)
    ret["skills"] = skills
    return ret


def apply_job(worksite, job, character, parttime=False):
    pass


def remove_apply(character, worksite):
    pass


def remove_job(character, job):
    pass


def get_job(character):
    pass


def create_storage(character, name, size):
    pass


def get_storage(name):
    pass


def set_storage_description(name, description):
    pass


def store(character, storage, item, amount):
    pass


def move(character, storage, item, amount, destination):
    pass


def storage_allow(character, storage):
    pass


def storage_disallow(character, storage):
    pass


def storage_steal(character, storage):
    pass


def storage_delete(storage):
    pass


def storage_remove(storage, item, amount):
    pass


def storage_resize(storage, size):
    pass


def storage_transfer(storage, recipient):
    pass


def storage_upgradte(storage, upgrade):
    pass


def worksite_create(character, type, name, storage, *args):
    pass


def get_worksite(worksite):
    pass


def delete_worksite(worksite):
    pass


def worksite_description(worksite, description):
    pass


def worksite_changestorage(worksite, storage):
    pass


def worksite_add(worksite, addition, *args):
    pass


def worksite_upgrade(worksite, upgrade, *args):
    pass


def worksite_hire(worksite, character, job, parttime=False):
    pass


def worksite_fire(worksite, character):
    pass


def worksite_salary(worksite, job, amount, money_store=None, frequency=None):
    pass


def create_job(worksite, job_name):
    pass