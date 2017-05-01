import redis
import random
import re
import time
import os
from subprocess import call
import threading
import json
import requests
from itertools import accumulate
from bisect import bisect
from unicodedata import name as unicode_name


chain_length = 2
max_words = 30
separator = '\x01'
stop_word = '\x02'
redis_conn = redis.Redis()
prefix = 'discord'

UNICODE_VERSION = 6

# Sauce: http://www.unicode.org/charts/PDF/U1F300.pdf
EMOJI_RANGES_UNICODE = {
    6: [
        ('\U0001F300', '\U0001F320'),
        ('\U0001F330', '\U0001F335'),
        ('\U0001F337', '\U0001F37C'),
        ('\U0001F380', '\U0001F393'),
        ('\U0001F3A0', '\U0001F3C4'),
        ('\U0001F3C6', '\U0001F3CA'),
        ('\U0001F3E0', '\U0001F3F0'),
        ('\U0001F400', '\U0001F43E'),
        ('\U0001F440', ),
        ('\U0001F442', '\U0001F4F7'),
        ('\U0001F4F9', '\U0001F4FC'),
        ('\U0001F500', '\U0001F53C'),
        ('\U0001F540', '\U0001F543'),
        ('\U0001F550', '\U0001F567'),
        ('\U0001F5FB', '\U0001F5FF')
    ],
    7: [
        ('\U0001F300', '\U0001F32C'),
        ('\U0001F330', '\U0001F37D'),
        ('\U0001F380', '\U0001F3CE'),
        ('\U0001F3D4', '\U0001F3F7'),
        ('\U0001F400', '\U0001F4FE'),
        ('\U0001F500', '\U0001F54A'),
        ('\U0001F550', '\U0001F579'),
        ('\U0001F57B', '\U0001F5A3'),
        ('\U0001F5A5', '\U0001F5FF')
    ],
    8: [
        ('\U0001F300', '\U0001F579'),
        ('\U0001F57B', '\U0001F5A3'),
        ('\U0001F5A5', '\U0001F5FF')
    ]
}


LEG_WITH_SOCKET = [
    132369, 132410, 137044, 132444, 132449, 132452, 132460, 133973, 133974,
    137037, 137038, 137039, 137040, 137041, 137042, 137043, 132378, 137045,
    137046, 137047, 137048, 137049, 137050, 137051, 137052, 137054, 137055,
    137220, 137223, 137276, 137382, 138854
]

ENCHANTABLE_SLOTS = ["neck", "back", "finger1", "finger2"]

API_KEY = "hjbuwscztbjgtkw3axcec8tsq7xs5t6c"
default_region = "us"

region_locale = {
    'us': ['us', 'en_US', 'en'],
    #    'kr': ['kr', 'ko_KR', 'ko'],
    #    'tw': ['tw', 'zh_TW', 'zh'],
    'eu': ['eu', 'en_GB', 'en']
}

NO_NAME_ERROR = '(No name found for this codepoint)'

def random_emoji(unicode_version = 6):
    if unicode_version in EMOJI_RANGES_UNICODE:
        emoji_ranges = EMOJI_RANGES_UNICODE[unicode_version]
    else:
        emoji_ranges = EMOJI_RANGES_UNICODE[-1]

    # Weighted distribution
    count = [ord(r[-1]) - ord(r[0]) + 1 for r in emoji_ranges]
    weight_distr = list(accumulate(count))

    # Get one point in the multiple ranges
    point = random.randrange(weight_distr[-1])

    # Select the correct range
    emoji_range_idx = bisect(weight_distr, point)
    emoji_range = emoji_ranges[emoji_range_idx]

    # Calculate the index in the selected range
    point_in_range = point
    if emoji_range_idx is not 0:
        point_in_range = point - weight_distr[emoji_range_idx - 1]

    # Emoji 😄
    emoji = chr(ord(emoji_range[0]) + point_in_range)
    emoji_name = unicode_name(emoji, NO_NAME_ERROR).capitalize()
    emoji_codepoint = "U+{}".format(hex(ord(emoji))[2:].upper())

    return (emoji)

def get_sockets(player_dictionary):
    """
    Return dict with total sockets and count of equipped gems and slots that are missing

    :param player_dictionary: Retrieved player dict from API
    :return: dict()
    """
    sockets = 0
    equipped_gems = 0

    for item in player_dictionary["items"]:
        if item in "averageItemLevel" or item in "averageItemLevelEquipped":
            continue

        if int(player_dictionary["items"][item]["id"]) in LEG_WITH_SOCKET:
            sockets += 1

        else:
            for bonus in player_dictionary["items"][item]["bonusLists"]:
                if bonus == 1808:  # 1808 is Legion prismatic socket bonus
                    sockets += 1

            if item in ["neck", "finger1", "finger2"]:
                if player_dictionary["items"][item][
                        "context"] == "trade-skill":
                    sockets += 1

        for ttip in player_dictionary["items"][item]["tooltipParams"]:
            if item in "mainHand" or item in "offHand":  # Ignore Relic
                continue
            if "gem" in ttip:  # Equipped gems are listed as gem0, gem1, etc...
                equipped_gems += 1

    return {"total_sockets": sockets, "equipped_gems": equipped_gems}


def get_enchants(player_dictionary):
    """
    Get count of enchants missing and slots that are missing
    :param player_dictionary:
    :return: dict()
    """
    missing_enchant_slots = []
    for slot in ENCHANTABLE_SLOTS:
        if "enchant" not in player_dictionary["items"][slot]["tooltipParams"]:
            missing_enchant_slots.append(slot)

    return {
        "enchantable_slots": len(ENCHANTABLE_SLOTS),
        "missing_slots": missing_enchant_slots,
        "total_missing": len(missing_enchant_slots)
    }


def get_raid_progression(player_dictionary, raid):
    r = [
        x for x in player_dictionary["progression"]["raids"]
        if x["name"] in raid
    ][0]
    normal = 0
    heroic = 0
    mythic = 0

    for boss in r["bosses"]:
        if boss["normalKills"] > 0:
            normal += 1
        if boss["heroicKills"] > 0:
            heroic += 1
        if boss["mythicKills"] > 0:
            mythic += 1

    return {
        "normal": normal,
        "heroic": heroic,
        "mythic": mythic,
        "total_bosses": len(r["bosses"])
    }


def get_mythic_progression(player_dictionary):
    achievements = player_dictionary["achievements"]
    plus_two = 0
    plus_five = 0
    plus_ten = 0

    if 33096 in achievements["criteria"]:
        index = achievements["criteria"].index(33096)
        plus_two = achievements["criteriaQuantity"][index]

    if 33097 in achievements["criteria"]:
        index = achievements["criteria"].index(33097)
        plus_five = achievements["criteriaQuantity"][index]

    if 33098 in achievements["criteria"]:
        index = achievements["criteria"].index(33098)
        plus_ten = achievements["criteriaQuantity"][index]

    return {"plus_two": plus_two, "plus_five": plus_five, "plus_ten": plus_ten}


def get_char(name, server, target_region):
    r = requests.get(
        "https://%s.api.battle.net/wow/character/%s/%s?fields=items+progression+achievements&locale=%s&apikey=%s"
        % (region_locale[target_region][0], server, name,
           region_locale[target_region][1], API_KEY))

    if r.status_code != 200:
        raise Exception("Could Not Find Character (No 200 from API)")

    player_dict = json.loads(r.text)

    r = requests.get(
        "https://%s.api.battle.net/wow/data/character/classes?locale=%s&apikey=%s"
        % (region_locale[target_region][0], region_locale[target_region][1],
           API_KEY))
    if r.status_code != 200:
        raise Exception("Could Not Find Character Classes (No 200 From API)")
    class_dict = json.loads(r.text)
    class_dict = {c['id']: c['name'] for c in class_dict["classes"]}

    equipped_ivl = player_dict["items"]["averageItemLevelEquipped"]
    sockets = get_sockets(player_dict)
    enchants = get_enchants(player_dict)
    nh_progress = get_raid_progression(player_dict, "The Nighthold")
    tov_progress = get_raid_progression(player_dict, "Trial of Valor")
    en_progress = get_raid_progression(player_dict, "The Emerald Nightmare")
    mythic_progress = get_mythic_progression(player_dict)

    armory_url = 'http://{}.battle.net/wow/{}/character/{}/{}/advanced'.format(
        region_locale[target_region][0], region_locale[target_region][2],
        server, name)

    return_string = ''
    return_string += "**%s** - **%s** - **%s %s**\n" % (
        name.title(), server.title(), player_dict['level'],
        class_dict[player_dict['class']])
    return_string += '<{}>\n'.format(armory_url)
    return_string += '```CSS\n'  # start Markdown

    # iLvL
    return_string += "Equipped Item Level: %s\n" % equipped_ivl

    # Mythic Progression
    return_string += "Mythics: +2: %s, +5: %s, +10: %s\n" % (
        mythic_progress["plus_two"], mythic_progress["plus_five"],
        mythic_progress["plus_ten"])

    # Raid Progression
    return_string += "EN: {1}/{0} (N), {2}/{0} (H), {3}/{0} (M)\n".format(
        en_progress["total_bosses"], en_progress["normal"],
        en_progress["heroic"], en_progress["mythic"])
    return_string += "TOV: {1}/{0} (N), {2}/{0} (H), {3}/{0} (M)\n".format(
        tov_progress["total_bosses"], tov_progress["normal"],
        tov_progress["heroic"], tov_progress["mythic"])
    return_string += "NH: {1}/{0} (N), {2}/{0} (H), {3}/{0} (M)\n".format(
        nh_progress["total_bosses"], nh_progress["normal"],
        nh_progress["heroic"], nh_progress["mythic"])

    # Gems
    return_string += "Gems Equipped: %s/%s\n" % (sockets["equipped_gems"],
                                                 sockets["total_sockets"])

    # Enchants
    return_string += "Enchants: %s/%s\n" % (
        enchants["enchantable_slots"] - enchants["total_missing"],
        enchants["enchantable_slots"])
    if enchants["total_missing"] > 0:
        return_string += "Missing Enchants: {0}".format(", ".join(enchants[
            "missing_slots"]))

    return_string += '```'  # end Markdown
    return return_string


def make_key(k):
    return '-'.join((prefix, k))


def profanity_filter(message):
    clean_words = [
        "unicorn", "artichoke", "Corned beef and cabbage", 'Trotsky-Leninism',
        "Chili with beans", "solipsism"
    ]
    bad_words_file = open('bad_words.txt', 'r')
    bad_words = set(line.strip('\n') for line in open('bad_words.txt'))
    clean_word = random.choice(clean_words)
    exp = '(%s)' % '|'.join(bad_words)
    r = re.compile(exp, re.IGNORECASE)
    return r.sub(clean_word, message)


def sanitize_message(message):
    return re.sub('[\"\']', '', message.lower())


def split_message(message):
    words = message.split()
    if len(words) > chain_length:
        words.append(stop_word)
        for i in range(len(words) - chain_length):
            yield words[i:i + chain_length + 1]


def generate_message(seed):
    key = seed
    gen_words = []
    for i in range(max_words):
        words = key.split(separator)
        gen_words.append(words[0])
        next_word = redis_conn.srandmember(make_key(key))
        if not next_word:
            break
        key = separator.join(words[1:] + [next_word.decode("utf=8")])
    return ' '.join(gen_words)
