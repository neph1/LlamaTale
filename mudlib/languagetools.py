import os
import re
import bisect

# genders are m,f,n
SUBJECTIVE = { "m": "he",  "f": "she", "n": "it"  }
POSSESSIVE = { "m": "his", "f": "her", "n": "its" }
OBJECTIVE  = { "m": "him", "f": "her", "n": "it"  }


def join(words, conj="and"):
    """join a list of words to 'a,b,c,d and e'"""
    if not words:
        return ""
    if len(words) == 1:
        return words[0]
    if len(words) == 2:
        return "%s %s %s" % (words[0], conj, words[1])
    return "%s, %s %s" % (", ".join(words[:-1]), conj, words[-1])


def a(word):
    """a or an? simplistic version: if the word starts with aeiou, returns an, otherwise a"""
    if not word:
        return ""
    if word.startswith(("a ", "an ")):
        return word
    if word.startswith(('a', 'e', 'i', 'o', 'u')):
        return "an " + word
    return "a " + word


def fullstop(sentence, punct="."):
    """adds a fullstop to the end of a sentence if needed"""
    sentence = sentence.rstrip()
    if sentence[-1] not in "!?.,;:-=":
        return sentence + punct
    else:
        return sentence


# adverbs are stored in a datafile next to this module
with open(os.path.join(os.path.dirname(__file__), "soul_adverbs.txt")) as adverbsfile:
    ADVERB_LIST = adverbsfile.read().splitlines()     # keep the list for prefix search
    ADVERBS = frozenset(ADVERB_LIST)


def adverb_by_prefix(prefix, amount=5):
    """
    Return a list of adverbs starting with the given prefix, up to the given amount
    """
    i = bisect.bisect_left(ADVERB_LIST, prefix)
    if i >= len(ADVERB_LIST):
        return []
    elif ADVERB_LIST[i].startswith(prefix):
        j = i + 1
        while amount > 1 and ADVERB_LIST[j].startswith(prefix):
            j += 1
            amount -= 1
        return ADVERB_LIST[i:j]
    else:
        return []


def possessive_letter(name):
    if not name:
        return ""
    if name[-1] in ('s', 'z', 'x'):
        return "'"        # tess' foot
    elif name.endswith(" own"):
        return ""         # your own...
    else:
        return "s"        # marks foot


def possessive(name):
    return name + possessive_letter(name)


def capital(string):
    if string:
        string = string[0].upper() + string[1:]
    return string


def split(string):
    """
    Split a string on whitespace, but keeps words enclosed in quotes (' or ") together.
    The quotes themselves are stripped out.
    """
    def removequotes(word):
        if word.startswith(('"', "'")) and word.endswith(('"', "'")):
            return word[1:-1].strip()
        return word
    return [removequotes(p) for p in re.split("( |\\\".*?\\\"|'.*?')", string) if p.strip()]
