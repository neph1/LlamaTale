"""
A player's 'soul', which provides a lot of possible emotes (verbs).

Written by Irmen de Jong (irmen@razorvine.net)
Based on ancient soul.c v1.2 written in LPC by profezzorn@nannymud (Fredrik Hübinette)
Only the verb table is more or less intact (with some additions and fixes).
The verb parsing and message generation have been rewritten.

The soul parsing has been moved to the Soul class in the base module.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from typing import Dict, Tuple, Sequence


DEFA = 1  # adds HOW+AT   (you smile happily at Fritz)
PREV = 2  # adds a WHO+HOW   (you ignore Fritz completely)
PHYS = 3  # adds a WHO+HOW+WHERE  (you stroke Anna softly on the shoulder)
SHRT = 4  # just adds a HOW, won't show a target  (you sweat profusely)
PERS = 5  # provide an alternate WHO text  (you shiver with fear / you fear Fritz)
SIMP = 6  # don't add stuff, the text itself has all escapes  (you snap your fingers at Fritz)
DEUX = 7  # a room text is provided with alternate spelling or wording  (you fall down and play dead / Player falls to the ground, dead)
QUAD = 8  # like DEUX, but also provides two more texts for when a target is used
FULL = 9  # not used yet

# escapes used: AT, HOW, IS, MSG, MY, POSS, SUBJ, WHAT, WHERE, WHO, YOUR
# adverbs tuple: (adverb, message, where)
# if message starts with a ' (single quote), it will appear *without quotes*.

# Note: several verbs here are commented out because they are replaced by
# real commands or don't fit the game mechanics very well. It doesn't cause problems
# because they're just emotes, but it causes less confusion to disable them here.

VERBS = {
    "flex":      (DEUX, None, "flex \nYOUR muscles \nHOW", "flexes \nYOUR muscles \nHOW"),
    "snort":     (SIMP, None, "snort$ \nHOW \nAT", "at"),
    "pant":      (SIMP, ("heavily", ), "pant$ \nHOW \nAT", "at"),
    "hmm":       (SIMP, None, "hmm$ \nHOW \nAT", "at"),
    "ack":       (SIMP, None, "ack$ \nHOW \nAT", "at"),
    "guffaw":    (SIMP, None, "guffaw$ \nHOW \nAT", "at"),
    "raise":     (SIMP, None, " \nHOW raise$ an eyebrow \nAT", "at"),
    "snap":      (SIMP, None, "snap$ \nYOUR fingers \nAT", "at"),
    "lust":      (DEFA, None, "", "for"),
    "burp":      (DEFA, ("rudely", ), "", "at"),
    "bump":      (DEFA, ("clumsily", ), "", "into"),
    "wink":      (DEFA, ("suggestively", ), "", "at"),
    "smile":     (DEFA, ("happily", ), "", "at"),
    "yawn":      (DEFA, None, "", "at"),
    "swoon":     (DEFA, ("romantically", ), "", "at"),
    "sneer":     (DEFA, ("disdainfully", ), "", "at"),
    "talk":      (SIMP, None, "want$ to talk \nAT \nHOW", "to"),
    "beam":      (DEFA, None, "", "at"),
    "point":     (DEFA, None, "", "at"),
    "grin":      (DEFA, ("evilly", ), "", "at"),
    "laugh":     (DEFA, None, "", "at"),
    "nod":       (DEFA, ("solemnly", ), "", "at"),
    "wave":      (DEFA, ("happily", ), "", "at"),
    "cackle":    (DEFA, ("gleefully", ), "", "at"),
    "chuckle":   (DEFA, None, "", "at"),
    "bow":       (DEFA, None, "", "to"),
    "surrender": (DEFA, None, "", "to"),
    "sit":       (DEFA, ("down", ), "", "in front of"),
    "stand":     (DEFA, ("up", ), "", "in front of"),
    "capitulate": (DEFA, ("unconditionally", ), "", "to"),
    "glare":     (DEFA, ("stonily", ), "", "at"),
    "giggle":    (DEFA, ("merrily", ), "", "at"),
    "groan":     (DEFA, None, "", "at"),
    "grunt":     (DEFA, None, "", "at"),
    "growl":     (DEFA, None, "", "at"),
    "breathe":   (DEFA, ("heavily", ), "", "at"),
    "argh":      (DEFA, None, "", "at"),
    "scowl":     (DEFA, ("darkly", ), "", "at"),
    "snarl":     (DEFA, None, "", "at"),
    "recoil":    (DEFA, ("with fear", ), "", "from"),
    "moan":      (DEFA, None, "", "at"),
    "howl":      (DEFA, ("in pain", ), "", "at"),
    "puke":      (DEFA, None, "", "on"),
    "drool":     (DEFA, None, "", "on"),
    "sneeze":    (DEFA, ("loudly", ), "", "at"),
    "spit":      (DEFA, None, "", "on"),
    "stare":     (DEFA, None, "", "at"),
    "whistle":   (DEFA, ("appreciatively", ), "", "at"),
    "applaud":   (DEFA, None, "", ""),
    "leer":      (DEFA, None, "", "at"),
    "agree":     (DEFA, None, "", "with"),
    "believe":   (PERS, None, "believe$ in \nMYself \nHOW", "believe$ \nWHO \nHOW"),
    "understand": (PERS, None, "understand$ \nHOW", "understand$ \nWHO \nHOW"),
    "disagree":  (DEFA, None, "", "with"),
    "fart":      (DEFA, None, "", "at"),
    "dance":     (DEFA, None, "", "with"),
    "spin":      (DEFA, ("dizzily",), "", "around"),
    "flirt":     (DEFA, None, "", "with"),
    "meow":      (DEFA, None, "", "at"),
    "bark":      (DEFA, None, "", "at"),
    "slide":     (SIMP, None, "slip$ and slide$ \nHOW"),
    "ogle":      (PREV, None, ""),
    "eye":       (PREV, ("suspiciously", ), ""),
    "pet":       (SIMP, None, "pet$ \nWHO \nHOW \nWHERE"),
    "barf":      (DEFA, None, "", "on"),
    "listen":    (DEFA, None, "", "to"),
    "hear":      (SIMP, None, "listen$ \nAT \nHOW", "to"),        # the same effect as listen
    "purr":      (DEFA, None, "", "at"),
    "curtsy":    (DEFA, None, "", "before"),
    "puzzle":    (SIMP, None, "look$ \nHOW puzzled \nAT", "at"),
    "grovel":    (DEFA, None, "", "before"),
    "tongue":    (SIMP, None, "stick$ \nYOUR tongue out \nHOW \nAT", "at"),
    "swing":     (SIMP, ("wildly", ), "swing$ \nYOUR arms \nHOW \nAT", "at"),
    "apologize": (DEFA, None, "", "to"),
    "sorry":     (SIMP, None, "apologize$ \nAT \nHOW", "to"),
    "complain":  (DEFA, None, "", "about"),
    "rotate":    (PERS, None, "rotate$ \nHOW", "rotate$ \nWHO \nHOW"),        # overridden by a cmd
    "excuse":    (PERS, None, " \nHOW excuse$ \nMYself", " \nHOW excuse$ \nMYself to \nWHO"),
    "beg":       (PERS, None, "beg$ \nHOW", "beg$ \nWHO for mercy \nHOW"),
    "fear":      (PERS, None, "shiver$ \nHOW with fear", "fear$ \nWHO \nHOW"),
    "headshake": (SIMP, None, "shake$ \nYOUR head \nAT \nHOW", "at"),
    "shake":     (SIMP, ("like a bowlful of jello", ), "shake$ \nAT \nHOW", ""),
    "jiggle":    (SIMP, ("like a bowlful of jello", ), "jiggle$ \nAT \nHOW", ""),
    "stink":     (PERS, None, "smell$ \nYOUR armpits. Eeeww!", "smell$ \nPOSS armpits. Eeeww!"),
    "grimace":   (SIMP, None, " \nHOW make$ an awful face \nAT", "at"),
    "stomp":     (PERS, None, "stomp$ \nYOUR foot \nHOW", "stomp$ on \nPOSS foot \nHOW"),
    "snigger":   (DEFA, ("jeeringly", ), "", "at"),
    "watch":     (QUAD, ("carefully", ), "watch the surroundings \nHOW", "watches the surroundings \nHOW",
                  "watch \nWHO \nHOW", "watches \nWHO \nHOW", ),
    "scratch":   (QUAD, (None, None, "on the head"), "scratch \nMYself \nHOW \nWHERE", "scratches \nMYself \nHOW \nWHERE",
                  "scratch \nWHO \nHOW \nWHERE", "scratches \nWHO \nHOW \nWHERE", ),
    "tap":       (PERS, ("impatiently", None, "on the shoulder"), "tap$ \nYOUR foot \nHOW", "tap$ \nWHO \nWHERE"),
    "wobble":    (SIMP, None, "wobble$ \nAT \nHOW", ""),
    "move":      (SIMP, ("thoughtfully", ), "move$ out of the way \nHOW", ""),
    "yodel":     (SIMP, None, "yodel$ a merry tune \nHOW", ""),
    "spray":     (SIMP, None, "spray$ \nHOW \nAT", "all over"),
    "spill":     (SIMP, None, "spill$ \nYOUR drink \nHOW \nAT", "all over"),
    "melt":      (PERS, ("in front of",), "melt$ from the heat", "melt$ \nHOW \nWHO"),
    "hello":     (PERS, None, "greet$ everyone \nHOW", "greet$ \nWHO \nHOW"),
    "hi":        (PERS, None, "greet$ everyone \nHOW", "greet$ \nWHO \nHOW"),
    "wait":      (SIMP, None, "wait$ \nHOW", ""),   # replaced by a command
    "grease":    (SIMP, ("like a shiatsu",), "grease$ \nWHO \nHOW"),
    "oil":       (SIMP, ("like a shiatsu",), "oil$ \nWHO \nHOW"),
    # "search":    (DEUX, ("thoroughly",), "search \nWHO \nHOW, where is it?", "searches \nWHO \nHOW, where is it?"), # replaced by command
    "sniff":     (PERS, None, "sniff$. What's that smell?", "sniff$ \nWHO. What's that smell?"),
    "smell":     (PERS, None, "sniff$. What's that smell?", "sniff$ \nWHO. What's that smell?"),
    "smoke":     (PERS, None, "smoke$ a cigar, and blow$ out the smoke.", "smoke$ a cigar, and blow$ the smoke at \nWHO."),

    # Message-based verbs
    "curse":     (PERS, None, "curse$ \nWHAT \nHOW", "curse$ \nWHO \nHOW"),
    "swear":     (SIMP, None, "swear$ \nWHAT \nAT \nHOW", "before"),
    "criticize": (PERS, None, "criticize$ \nWHAT \nHOW", "criticize$ \nWHO \nHOW"),
    "lie":       (PERS, None, "lie$ \nMSG \nHOW", "lie$ to \nWHO \nHOW"),
    "mutter":    (PERS, (None, "ehh..."), "mutter$ \nMSG \nHOW", "mutter$ \nMSG to \nWHO \nHOW"),
    # "say":      (SIMP, (None, "'nothing"), " say$ \nAT: \nWHAT", "to"),    # replaced by a command
    "babble":    (SIMP, ("incoherently", "'something"), "babble$ \nMSG \nHOW \nAT", "to"),
    "chant":     (SIMP, (None, "Hare Krishna Krishna Hare Hare"), " \nHOW chant$: \nWHAT", ""),
    "sing":      (SIMP, None, "sing$ \nWHAT \nHOW \nAT", "to"),
    "hiss":      (QUAD, None, "hiss \nMSG \nHOW", "hisses \nMSG \nHOW", "hiss \nMSG to \nWHO \nHOW", "hisses \nMSG to \nWHO \nHOW", ),
    "answer":    (SIMP, (None, "ehh..."), " \nHOW answer$ \nAT: \nWHAT", ""),
    "reply":     (QUAD, (None, "ehh..."), " \nHOW reply: \nWHAT", " \nHOW replies: \nWHAT",
                  " \nHOW reply to \nWHO: \nWHAT", " \nHOW replies to \nWHO: \nWHAT"),
    "exclaim":   (SIMP, (None, "no way"), " \nHOW exclaim$ \nAT: \nWHAT!", ""),
    "quote":     (SIMP, None, " \nHOW quote$ \nAT \nMSG", "to"),
    "ask":       (SIMP, (None, "ehh..."), " \nHOW ask$ \nAT: \nWHAT?", ""),
    "request":   (SIMP, (None, "a moment"), " \nHOW request$ \nAT \nWHAT", ""),
    "consult":   (SIMP, None, " \nHOW consult$ \nAT \nWHAT", ""),
    "mumble":    (SIMP, None, "mumble$ \nMSG \nHOW \nAT", "to"),
    "murmur":    (SIMP, None, "murmur$ \nMSG \nHOW \nAT", "to"),
    # "scream":    (SIMP, ("loudly", ), "scream$ \nMSG \nHOW \nAT", "at"),     # replaced by a command
    # "yell":     (SIMP, ("in a high pitched voice", ), "yell$ \nMSG \nHOW \nAT", "at"),    # replaced by a command
    "command":   (SIMP, (None, "follow orders"), "command$ \nWHO \nHOW to \nWHAT"),
    "utter":     (SIMP, (None, "ehh..."), " \nHOW utter$ \nMSG \nAT", "to"),
    "whisper":   (SIMP, None, "whisper$ \nMSG \nHOW \nAT", "to"),
    # "emote":    (DEUX, None, "emote: player \nWHAT", " \nWHAT"),   # replaced by a command

    # Verbs that require a person
    "glance":    (SIMP, None, "glance$ \nHOW at \nWHO"),
    "hide":      (SIMP, None, "hide$ \nHOW behind \nWHO"),
    "finger":    (SIMP, None, "give$ \nWHO the finger"),
    "mercy":     (SIMP, None, "beg$ \nWHO for mercy"),
    "jerk":      (SIMP, ("briskly", ), "jerk$ \nWHO \nHOW", ""),
    "insult":    (SIMP, ("angrily", ), " \nHOW spew$ profanities at \nWHO"),
    "gripe":     (PREV, None, "to"),
    "peer":      (PREV, None, "at"),
    "gaze":      (PREV, None, "at"),
    "chase":     (PREV, ("angrily",), "after"),
    "remember":  (SIMP, None, "remember$ \nAT \nHOW", ""),
    "surprise":  (PREV, None, ""),
    "pounce":    (PHYS, ("playfully", ), ""),
    "feel":      (PHYS, ("softly", ), ""),
    "bite":      (PERS, None, " \nHOW bite$ \nYOUR lip", "bite$ \nWHO \nHOW \nWHERE"),
    "lick":      (SIMP, None, "lick$ \nWHO \nHOW \nWHERE"),
    "caper":     (PERS, ("merrily", ), "caper$ \nHOW about", "caper$ around \nWHO \nHOW"),
    "beep":      (PERS, ("triumphantly", None, "on the nose"), " \nHOW beep$ \nMYself \nWHERE", " \nHOW beep$ \nWHO \nWHERE"),
    "blink":     (PERS, None, "blink$ \nHOW", "blink$ \nHOW at \nWHO"),
    "knock":     (PHYS, (None, None, "on the head"), ""),
    "bonk":      (PHYS, (None, None, "on the head"), ""),
    "bop":       (PHYS, (None, None, "on the head"), ""),
    "stroke":    (PHYS, (None, None, "on the cheek"), ""),
    "shove":     (PHYS, ("briskly", None, "to the side"), ""),
    "push":      (PHYS, (None, None, "to the side"), ""),
    "pull":      (SIMP, None, "pull$ at \nWHO"),
    "rub":       (PHYS, ("gently", None, "on the back"), ""),
    "hold":      (PHYS, (None, None, "in \nYOUR arms"), ""),
    "embrace":   (PHYS, (None, None, "in \nYOUR arms"), ""),
    "handshake": (SIMP, None, "shake$ hands with \nWHO", ""),
    "tickle":    (PREV, None, ""),
    "worship":   (PREV, None, ""),
    "admire":    (PREV, None, ""),
    "mock":      (PREV, None, ""),
    "tease":     (PREV, None, ""),
    "taunt":     (PREV, None, ""),
    "strangle":  (PREV, None, ""),
    "hate":      (PREV, None, ""),
    "kill":      (PREV, None, ""),
    "attack":    (PREV, None, ""),
    "fight":     (PREV, None, ""),
    "fondle":    (PREV, None, ""),
    "nominate":  (PREV, None, ""),
    "startle":   (PREV, None, ""),
    # "lift":     (PREV, ("from the floor", ), ""),   # doesn't fit game mechanics
    "turn":      (PREV, None, "\nYOUR head towards"),
    "squeeze":   (PREV, ("fondly", ), ""),
    "comfort":   (PREV, None, ""),
    "nudge":     (PHYS, ("suggestively", ), ""),
    "slap":      (PHYS, (None, None, "in the face"), ""),
    "hit":       (PHYS, (None, None, "in the face"), ""),
    "kick":      (PHYS, ("hard", ), ""),
    "tackle":    (SIMP, None, "tackle$ \nWHO \nHOW", ""),
    # "tell":     (SIMP, None, "tell$ \nWHO \nMSG", ""),     # replaced by a command
    "spank":     (PHYS, (None, None, "on the butt"), ""),
    "pat":       (PHYS, (None, None, "on the head"), ""),
    "punch":     (DEUX, (None, None, "in the eye"), "punch \nWHO \nHOW \nWHERE", "punches \nWHO \nHOW \nWHERE"),
    "hug":       (PREV, None, ""),
    "want":      (PREV, None, ""),
    "pinch":     (DEUX, None, "pinch \nWHO \nHOW \nWHERE", "pinches \nWHO \nHOW \nWHERE"),
    "kiss":      (DEUX, None, "kiss \nWHO \nHOW \nWHERE", "kisses \nWHO \nHOW \nWHERE"),
    "caress":    (DEUX, (None, None, "on the cheek"), "caress \nWHO \nHOW \nWHERE", "caresses \nWHO \nHOW \nWHERE"),
    "smooch":    (DEUX, None, "smooch \nWHO \nHOW", "smooches \nWHO \nHOW"),
    "envy":      (DEUX, None, "envy \nWHO \nHOW", "envies \nWHO \nHOW"),
    "touch":     (DEUX, None, "touch \nWHO \nHOW \nWHERE", "touches \nWHO \nHOW \nWHERE"),
    "knee":      (PHYS, (None, None, "where it hurts"), ""),
    "love":      (PREV, None, ""),
    "adore":     (PREV, None, ""),
    "grope":     (PREV, None, ""),
    "poke":      (PHYS, (None, None, "in the ribs"), ""),
    "snuggle":   (PREV, None, ""),
    "kneel":     (SIMP, None, " \nHOW fall$ on \nYOUR knees \nAT", "in front of"),
    "trust":     (PREV, None, ""),
    "like":      (PREV, None, ""),
    "greet":     (PREV, None, ""),
    "welcome":   (PREV, None, ""),
    "thank":     (PREV, None, ""),
    "cuddle":    (PREV, None, ""),
    "salute":    (PREV, None, ""),
    "french":    (SIMP, None, "give$ \nWHO a REAL kiss, it seems to last forever"),
    "nibble":    (SIMP, None, "nibble$ \nHOW on \nPOSS ear"),
    "ruffle":    (SIMP, None, "ruffle$ \nPOSS hair \nHOW"),
    "ignore":    (PREV, None, ""),
    "forgive":   (PREV, None, ""),
    "congratulate": (PREV, None, ""),
    "ayt":       (SIMP, None, "wave$ \nYOUR hand in front of \nPOSS face, \nIS \nSUBJ \nHOW there?"),
    "judge":     (PREV, None, "", ),

    # Verbs that don't need, nor use persons
    "roll":      (SIMP, ("to the ceiling", ), "roll$ \nYOUR eyes \nHOW"),
    "boggle":    (SIMP, None, "boggle$ \nHOW at the concept"),
    "cheer":     (SHRT, ("enthusiastically", ), ""),
    "twiddle":   (SIMP, None, "twiddle$ \nYOUR thumbs \nHOW"),
    "wiggle":    (SIMP, None, "wiggle$ \nYOUR bottom \nAT \nHOW", "at"),
    "wrinkle":   (SIMP, None, "wrinkle$ \nYOUR nose \nAT \nHOW", "at"),
    "thumb":     (SIMP, None, " \nHOW suck$ \nYOUR thumb"),
    "flip":      (SIMP, None, "flip$ \nHOW head over heels"),
    "cry":       (DEUX, None, "cry \nHOW", "cries \nHOW"),
    "ah":        (DEUX, None, "go 'ah' \nHOW", "goes 'ah' \nHOW"),
    "halt!":     (DEUX, None, "go 'Halt! Hammerzeit!' \nHOW", "goes 'Halt! Hammerzeit!' \nHOW"),
    "stop!":     (DEUX, None, "go 'Stop! Hammertime!' \nHOW", "goes 'Stop! Hammertime!' \nHOW"),
    "clear":     (SIMP, None, "clear$ \nYOUR throat \nHOW"),
    "sob":       (SHRT, None, ""),
    "lag":       (SHRT, ("helplessly", ), ""),
    "whine":     (SHRT, None, ""),
    "cringe":    (SIMP, ("in terror", ), "cringe$ \nHOW"),
    "sweat":     (SHRT, None, ""),
    "gurgle":    (SHRT, None, ""),
    "grumble":   (SHRT, None, ""),
    "panic":     (SHRT, None, ""),
    "pace":      (SIMP, ("impatiently", ), "start$ pacing \nHOW"),
    "pale":      (SIMP, None, "turn$ white as ashes \nHOW"),
    "die":       (DEUX, None, " \nHOW fall down and play dead", " \nHOW falls to the ground, dead"),
    # "sleep":    (DEUX, ("soundly", ), "fall asleep \nHOW", "falls asleep \nHOW"),
    "sleep":     (SIMP, None, "yawn$ sleepily"),
    # "wake":     (SIMP, ("groggily", ), "awake$ \nHOW"),
    "wake":      (DEUX, None, "are awake", "is awake"),
    # "awake":    (SIMP, ("groggily", ), "awake$ \nHOW"),
    "awake":     (DEUX, None, "are awake", "is awake"),
    "stumble":   (SHRT, None, ""),
    "bounce":    (SHRT, ("up and down", ), ""),
    "sulk":      (SHRT, ("in the corner", ), ""),
    "strut":     (SHRT, ("proudly", ), ""),
    "snivel":    (SHRT, ("pathetically", ), ""),
    "snore":     (SHRT, None, ""),
    "clue":      (SIMP, None, "need$ a clue \nHOW"),
    "stupid":    (SIMP, None, "look$ \nHOW stupid"),
    "bored":     (SIMP, None, "look$ \nHOW bored"),
    "repent":    (SIMP, None, "repent$ \nYOUR sins"),
    "snicker":   (SHRT, None, ""),
    "smirk":     (SHRT, None, ""),
    "jump":      (SIMP, ("up and down in aggravation", ), "jump$ \nHOW"),
    "squint":    (SHRT, None, ""),
    "huff":      (SHRT, None, ""),
    "puff":      (SHRT, None, ""),
    "fume":      (SHRT, None, ""),
    "steam":     (SHRT, None, ""),
    "choke":     (SHRT, None, ""),
    "faint":     (SHRT, None, ""),
    "shrug":     (SHRT, None, ""),
    "pout":      (SHRT, None, ""),
    "hiccup":    (SHRT, None, ""),
    "frown":     (SHRT, None, ""),
    "pray":      (SIMP, None, "mumble$ a short prayer \nAT", "to"),
    "gasp":      (SHRT, ("in astonishment", ), ""),
    "think":     (SHRT, ("carefully", ), ""),
    "ponder":    (SHRT, ("over some problem", ), ""),
    "wonder":    (DEFA, None, "", "at"),
    "clap":      (SHRT, None, ""),
    "sigh":      (SHRT, None, ""),
    "cough":     (SHRT, ("noisily", ), ""),
    "shiver":    (SHRT, ("from the cold", ), ""),
    "tremble":   (SHRT, None, ""),
    "twitch":    (DEUX, None, "twitch \nHOW", "twitches \nHOW"),
    "bitch":     (DEUX, None, "bitch \nHOW", "bitches \nHOW"),
    "blush":     (DEUX, None, "blush \nHOW", "blushes \nHOW"),
    "stretch":   (DEUX, None, "stretch \nHOW", "stretches \nHOW"),
    "relax":     (DEUX, None, "relax \nHOW", "relaxes \nHOW"),
    "duck":      (PERS, None, "duck$ \nHOW out of the way", "duck$ \nHOW out of \nPOSS way"),
}  # type: Dict[str, Tuple]

assert all(v[1] is None or type(v[1]) is tuple for v in VERBS.values()), "Second specifier in verb list must be None or tuple, not str"

AGGRESSIVE_VERBS = {
    "attack", "barf", "bitch", "bite", "bonk", "bop", "bump", "burp", "caress", "chase", "curse", "feel", "fight",
    "finger", "fondle", "french", "grease", "grimace", "grope", "growl", "guffaw", "handshake", "hit", "hold", "hug",
    "insult", "jerk", "jiggle", "kick", "kill", "kiss", "knee", "knock", "lick", "mock", "nibble", "nudge", "oil",
    "pat", "pet", "pinch", "poke", "pounce", "puke", "push", "pull", "punch", "rotate", "rub", "ruffle", "scowl",
    "scratch", "shake", "shove", "slap", "smooch", "sneer", "snigger", "snuggle", "spank", "spill", "spit", "spray",
    "squeeze", "startle", "stomp", "strangle", "stroke", "surprise", "swing", "tackle", "tap", "taunt", "tease",
    "tickle", "tongue", "touch", "wiggle", "wobble", "wrinkle"
}

assert AGGRESSIVE_VERBS.issubset(VERBS.keys())

NONLIVING_OK_VERBS = {
    "admire", "adore", "answer", "argh", "ask", "babble", "barf", "bark", "beam",
    "bite", "blink", "bow", "breathe", "bump", "cackle", "caper", "capitulate",
    "chuckle", "complain", "cuddle", "curse", "drool", "embrace", "eye", "fear",
    "feel", "finger", "fondle", "gaze", "giggle", "glare", "glance", "grimace", "grin", "groan",
    "grope", "growl", "grunt", "guffaw", "hate", "headshake", "hide", "hiss",
    "hmm", "ignore", "jerk", "judge", "kick", "laugh", "leer", "lick", "like", "listen",
    "love", "lust", "meow", "moan", "mumble", "murmur", "mutter", "nod", "nominate",
    "ogle", "peer", "point", "puke", "pull", "push", "purr", "puzzle", "quote",
    "raise", "recoil", "reply", "rotate", "scowl", "shake",
    "shove", "sing", "smile", "snap", "snarl", "sneer", "sneeze", "smell", "sniff",
    "snigger", "snort", "spill", "spin", "spit", "spray", "stare", "surrender",
    "swing", "squeeze", "tongue", "touch", "trust", "turn", "understand", "utter", "want",
    "watch", "wave", "wiggle", "wobble", "worship", "wrinkle", "yawn"
}

assert NONLIVING_OK_VERBS.issubset(VERBS.keys())

MOVEMENT_VERBS = {"enter", "climb", "crawl", "go", "move"}     # used to move through an exit. Note: 'flee' and 'run' are special


def adjust_available_verbs(allowed_verbs: Sequence[str]=None, remove_verbs: Sequence[str]=[], add_verbs: Dict[str, Tuple]={}) -> None:
    """Adjust the available verbs"""
    global VERBS, AGGRESSIVE_VERBS, NONLIVING_OK_VERBS, MOVEMENT_VERBS
    if allowed_verbs is not None:
        for v in allowed_verbs:
            if v not in VERBS:
                raise KeyError(v)
        allowed_verbs_set = set(allowed_verbs)
        VERBS = {v: k for v, k in VERBS.items() if v in allowed_verbs_set}
        AGGRESSIVE_VERBS &= allowed_verbs_set
        NONLIVING_OK_VERBS &= allowed_verbs_set
        MOVEMENT_VERBS &= allowed_verbs_set
    for v in remove_verbs:
        del VERBS[v]
        AGGRESSIVE_VERBS.discard(v)
        NONLIVING_OK_VERBS.discard(v)
        MOVEMENT_VERBS.discard(v)
    VERBS.update(add_verbs)


ACTION_QUALIFIERS = {
    # qualifier -> (actionmsg, roommsg, use room actionstr)
    "suddenly": ("suddenly %s", "suddenly %s", True),
    "fail": ("try to %s, but fail miserably", "tries to %s, but fails miserably", False),
    "again": ("%s again", "%s again", True),
    "pretend": ("pretend to %s", "pretends to %s", False),
    "dont": ("don't %s", "doesn't %s", False),
    "don't": ("don't %s", "doesn't %s", False),
    "attempt": ("attempt to %s, without much success", "attempts to %s, without much success", False)
}

NEGATING_QUALIFIERS = {"fail", "pretend", "dont", "don't", "attempt"}

assert NEGATING_QUALIFIERS.issubset(ACTION_QUALIFIERS.keys())

BODY_PARTS = {
    "hand": "on the hand",
    "forehead": "on the forehead",
    "head": "on the head",
    "kneecap": "on the kneecap",
    "ankle": "in the ankle",
    "knee": "on the knee",
    "face": "in the face",
    "hurts": "where it hurts",
    "nuts": "where it hurts",
    "eye": "in the eye",
    "ear": "on the ear",
    "stomach": "in the stomach",
    "butt": "on the butt",
    "behind": "on the behind",
    "leg": "on the leg",
    "foot": "on the foot",
    "toe": "on the right toe",
    "nose": "on the nose",
    "neck": "in the neck",
    "back": "on the back",
    "arm": "on the arm",
    "chest": "on the chest",
    "cheek": "on the cheek",
    "side": "in the side",
    "everywhere": "everywhere",
    "shoulder": "on the shoulder",
    "feet": "on the feet",
    "tail": "on the tail",
    "wing": "on the wing",
    "wings": "on the wings"
}
