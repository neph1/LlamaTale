"""
Language processing related operations.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import bisect
import collections
import re
from typing import List, Iterable

from . import vfs


# genders are m,f,n
SUBJECTIVE = {"m": "he", "f": "she", "n": "it"}
POSSESSIVE = {"m": "his", "f": "her", "n": "its"}
OBJECTIVE = {"m": "him", "f": "her", "n": "it"}
GENDERS = {"m": "male", "f": "female", "n": "neuter"}


class OrderedCounter(collections.Counter, collections.OrderedDict):     # type: ignore
    """A counter that remembers the order in which things are being counted."""
    @classmethod
    def fromkeys(cls, iterable, v=None):
        # There is no equivalent method for counters because setting v=1 means that no element can have a count greater than one.
        raise NotImplementedError('OrderedCounter.fromkeys() is undefined.  Use OrderedCounter(iterable) instead.')


def join(words: Iterable[str], conj: str="and", group_multi: bool=True) -> str:
    """
    Join a list of words to 'a,b,c, and e'
    If a word occurs multiple times (and group_multi=True),
    show 'thing and thing' as 'two things' instead.
    """
    def apply_amount(count, word):
        prefix, _, rest = word.partition(' ')
        if rest and prefix in {"the", "a", "an"}:
            # remove the article when we're dealing with multiple occurrences
            word = rest
        return spell_number(count) + " " + pluralize(word)
    if not words:
        return ""
    words = list(words)
    if len(words) == 1:
        return words[0]
    if group_multi and len(set(words)) == 1:
        return apply_amount(len(words), words[0])  # all words are the same
    if len(words) == 2:
        return "%s %s %s" % (words[0], conj, words[1])
    if group_multi:
        counts = OrderedCounter(words)
        words = []
        for word, count in counts.items():
            if count == 1:
                words.append(word)
            else:
                words.append(apply_amount(count, word))
        return join(words, conj, group_multi=False)
    return "%s, %s %s" % (", ".join(words[:-1]), conj, words[-1])


def fullstop(sentence: str, punct: str=".") -> str:
    """adds a fullstop to the end of a sentence if needed"""
    sentence = sentence.rstrip()
    if sentence.endswith(('!', '?', '.', ';', ':', '-', '=')):
        return sentence
    return sentence + punct


# adverbs are stored in a datafile next to this module
__ADVERB_LIST = list(sorted(vfs.internal_resources["soul_adverbs.txt"].text.splitlines()))   # is used for prefix search
ADVERBS = frozenset(__ADVERB_LIST)


def adverb_by_prefix(prefix: str, amount: int=5) -> List[str]:
    """
    Return a list of adverbs starting with the given prefix, up to the given amount
    Uses binary search in the sorted adverbs list, O(log n)
    """
    i = bisect.bisect_left(__ADVERB_LIST, prefix)
    if i >= len(__ADVERB_LIST):
        return []
    elif __ADVERB_LIST[i].startswith(prefix):
        j = i + 1
        amount = min(amount, len(__ADVERB_LIST) - i)   # avoid reading past the end of the list
        while amount > 1 and __ADVERB_LIST[j].startswith(prefix):
            j += 1
            amount -= 1
        return __ADVERB_LIST[i:j]
    else:
        return []


def possessive_letter(name: str) -> str:
    if not name:
        return ""
    if name[-1] in ('s', 'z', 'x'):
        return "'s"        # tess's foot
    elif name.endswith(" own"):
        return ""         # your own...
    else:
        return "'s"        # mark's foot


def possessive(name: str) -> str:
    return name + possessive_letter(name)


def capital(string: str) -> str:
    # cannot use string.capitalize because that lowercases the rest
    if string:
        string = string[0].upper() + string[1:]
    return string


def fullverb(verb: str) -> str:
    """return the full verb: shoot->shooting, poke->poking"""
    if verb[-1] == "e":
        return verb[:-1] + "ing"
    return verb + "ing"


def split(string: str) -> List[str]:
    """
    Split a string on whitespace, but keeps words enclosed in quotes (' or ") together.
    The quotes themselves are stripped out.
    """
    def removequotes(word):
        if word.startswith(('"', "'")) and word.endswith(('"', "'")):
            return word[1:-1].strip()
        return word
    return [removequotes(p) for p in re.split("( |\\\".*?\\\"|'.*?')", string) if p.strip()]


__number_words = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"
]

__tens_words = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"
]

__number_ordinals = [
    "zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
    "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth"
]

__tens_ordinals = [
    "", "tenth", "twentieth", "thirtieth", "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth"
]


def spell_number(number: float) -> str:
    """
    Return a spelling of the number. Supports positive and negative ints,
    floats, and recognises popular fractions such as 0.5 and 0.25.
    Numbers that are very near a whole number are also returned as "about N".
    Any fraction that can not be spelled out (or is larger than +/- 100) will
    not be spelled out in words, but returned in numerical form.
    """
    def spell_positive_int(n):
        if n <= 20:
            return __number_words[n]
        tens, ones = divmod(n, 10)
        if tens <= 9:
            if ones > 0:
                return __tens_words[tens] + "-" + __number_words[ones]
            return __tens_words[tens]
        return str(n)
    sign = ""
    orig_number = number
    if number < 0:
        sign = "minus "
        number = -number
    whole, fraction = divmod(number, 1)
    whole = int(whole)
    if fraction == 0.0:
        return sign + spell_positive_int(whole)
    elif fraction == 0.5:
        return sign + spell_positive_int(whole) + " and a half"
    elif fraction == 0.25:
        return sign + spell_positive_int(whole) + " and a quarter"
    elif fraction == 0.75:
        return sign + spell_positive_int(whole) + " and three quarters"
    elif fraction > 0.995:
        return "about " + sign + spell_positive_int(whole + 1)
    elif fraction < 0.005:
        return "about " + sign + spell_positive_int(whole)
    return str(orig_number)  # can't spell other fractions


def spell_ordinal(number: int) -> str:
    """Return a spelling of the ordinal number. Supports positive and negative ints."""
    number = int(number)
    n = abs(number)
    sign = "" if number >= 0 else "minus "
    if n <= 20:
        return sign + __number_ordinals[n]
    tens, ones = divmod(n, 10)
    if tens <= 9:
        if ones > 0:
            return sign + __tens_words[tens] + "-" + __number_ordinals[ones]
        return __tens_ordinals[tens]
    return ordinal(n)


def ordinal(number: int) -> str:
    """return the simple ordinal (1st, 3rd, 8th etc) of a number. Supports positive and negative ints."""
    suf = "th"
    number = int(number)
    anum = abs(number)
    if (anum % 100) // 10 != 1:
        n = anum % 10
        if n == 1:
            suf = "st"
        elif n == 2:
            suf = "nd"
        elif n == 3:
            suf = "rd"
    return "%d%s" % (number, suf)


# words that cannot be prefixed with 'a' or 'an'
no_a_words = {
    "he", "she", "it", "his", "her", "its", "him", "her", "some",
    "a", "an", "the", "any", "none", "nothing", "nobody", "nowhere",
    "everyone", "everybody", "everywhere", "everything",
    "someone", "somebody", "somewhere", "something",
    "anyone", "anybody", "anywhere", "anything",
} | set(__number_words) | set(__tens_words)


def a(noun_phrase: str) -> str:
    """prefix an article 'a' or 'an' (if possible)"""
    w = noun_phrase.partition(" ")[0].lower()
    if w in no_a_words or w.endswith("'s"):
        return noun_phrase
    if w in __number_ordinals or w in __tens_ordinals:
        return "the " + noun_phrase
    # algorithm adapted from CPAN package Lingua-EN-Inflect by Damian Conway
    if not noun_phrase:
        return ""
    if noun_phrase.lower() in {"a", "an"}:
        return "an " + noun_phrase
    m = re.search(r"\w+", noun_phrase)
    if m:
        word = m.group(0)
        if word.lower() in {"a", "an"}:
            return noun_phrase
    else:
        return 'an ' + noun_phrase

    wordi = word.lower()
    if wordi.startswith(('euler', 'heir', 'honest', 'hono')):
        return 'an ' + noun_phrase

    if wordi.startswith('hour') and not wordi.startswith('houri'):
        return 'an ' + noun_phrase

    if len(word) == 1:
        if wordi in 'aefhilmnorsx':
            return 'an ' + noun_phrase
        else:
            return 'a ' + noun_phrase

    if re.match(r'(?!FJO|[HLMNS]Y.|RY[EO]|SQU|'
                r'(F[LR]?|[HL]|MN?|N|RH?|S[CHKLMNPTVW]?|X(YL)?)[AEIOU])'
                r'[FHLMNRSX][A-Z]', word):
        return 'an ' + noun_phrase

    for regex in (r'^e[uw]', r'^onc?e\b',
                  r'^uni([^nmd]|mo)', '^u[bcfhjkqrst][aeiou]'):
        if re.match(regex, wordi):
            return 'a ' + noun_phrase

    # original regex was /^U[NK][AIEO]?/ but that matches UK, UN, etc.
    if re.match('^U[NK][AIEO]', word):
        return 'a ' + noun_phrase
    elif word == word.upper():
        if wordi[0] in 'aefhilmnorsx':
            return 'an ' + noun_phrase
        else:
            return 'a ' + noun_phrase

    if wordi[0] in 'aeiou':
        return 'an ' + noun_phrase

    if re.match(r'^y(b[lor]|cl[ea]|fere|gg|p[ios]|rou|tt)', wordi):
        return 'an ' + noun_phrase
    else:
        return 'a ' + noun_phrase


def A(word: str) -> str:
    """prefix an article 'A' or 'An' capitalized. (if possible)"""
    return capital(a(word))


__plural_irregularities = {
    "mouse": "mice",
    "child": "children",
    "person": "people",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "goose": "geese",
    "tooth": "teeth",
    "aircraft": "aircraft",
    "fish": "fish",
    "headquarters": "headquarters",
    "sheep": "sheep",
    "species": "species",
    "cattle": "cattle",
    "scissors": "scissors",
    "trousers": "trousers",
    "pants": "pants",
    "tweezers": "tweezers",
    "congratulations": "congratulations",
    "pyjamas": "pyjamas",
    "photo": "photos",
    "piano": "pianos",
    # probably more, but these will have to do for now
}


def pluralize(word: str, amount: float=2) -> str:
    if amount == 1:
        return word
    if word in __plural_irregularities:
        return __plural_irregularities[word]
    if word.endswith("is"):
        return word[:-2] + "es"
    if word.endswith("z"):
        return word + "zes"
    if word.endswith("s") or word.endswith("ch") or word.endswith("x") or word.endswith("sh"):
        return word + "es"
    if word.endswith("y"):
        if len(word) > 1 and word[-2] in "aeiou":
            return word + "s"
        return word[:-1] + "ies"
    if word.endswith("f"):
        return word[:-1] + "ves"
    if word.endswith("fe"):
        return word[:-2] + "ves"
    if word.endswith("o") and len(word) > 1 and word[-2] not in "aeiouy":
        return word + "es"
    return word + "s"


def yesno(value: str) -> bool:
    value = value.lower() if value else ""
    if value in {"y", "yes", "sure", "yep", "yeah", "yessir", "sure thing"}:
        return True
    if value in {"n", "no", "nope", "no way", "hell no"}:
        return False
    raise ValueError("That is not an understood yes or no.")


def validate_gender(value: str) -> str:
    value = value.lower() if value else ""
    if value in GENDERS:
        return value
    if len(value) > 1:
        if value[0] in GENDERS and GENDERS[value[0]] == value:
            return value
    raise ValueError("That is not a valid gender.")


def validate_gender_mf(value: str) -> str:
    value = value.lower() if value else ""
    genders = dict(GENDERS)
    genders.pop("n")
    if value in genders:
        return value
    if len(value) > 1:
        if value[0] in genders and genders[value[0]] == value:
            return value
    raise ValueError("That is not a valid gender.")

