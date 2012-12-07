"""
Race defintions.
Races adapted from Dark Souls mudlib (a superset of the races from Nightmare mudlib).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from __future__ import absolute_import, print_function, division, unicode_literals

flying_races = {'avidryl', 'bat', 'bird', 'bot', 'demon', 'dragon', 'faerie', 'gargoyle', 'griffin', 'insect', 'pegasus', 'vehicle', 'wraith'}
limbless_combat_races = {'android', 'blob', 'bot', 'elemental', 'fish', 'god', 'mech', 'plant', 'slug', 'snake', 'strider', 'tree', 'vehicle', 'viper'}
limbless_races = {'blob', 'elemental', 'fish', 'slug', 'snake', 'viper'}
nonbiting_races = {'android', 'bot', 'cow', 'dark-elf', 'deer', 'dummy', 'elemental', 'elf', 'faerie', 'god', 'golem', 'mech', 'plant', 'strider', 'vehicle', 'vulcan'}
swimming_races = {'amphibian', 'android', 'artrell', 'bear', 'bot', 'bugbear', 'cat', 'dark-elf', 'demi-god', 'demon', 'dragon', 'elephant', 'elf', 'fish', 'giant', 'gnoll', 'gnome', 'goblin', 'god', 'half-elf', 'halfling', 'hobbit', 'human', 'kender', 'lizard', 'nymph', 'replicant', 'rodent', 'troll', 'vehicle', 'vulcan'}
nonmeat_races = {'android', 'balrog', 'bot', 'dummy', 'elemental', 'god', 'golem', 'mech', 'plant', 'strider', 'tree', 'vehicle', 'wraith'}
player_races = {'dwarf', 'elf', 'half-elf', 'half-orc', 'halfling', 'human', 'orc'}  # races that can be used by players

# BODY_TYPES (every race has exactly one of the following body types)
B_HUMANOID, B_QUADRUPED, B_BIPED, B_CHIROPTEROID, B_INSECTOID, B_TENTACLED, B_ARTHROPOD, B_CRUSTACEAN, B_PINNIPED, \
    B_CETACEAN, B_FISH, B_OCTOPOID, B_NEBULOUS, B_CHIMAERA, B_SNAKE, B_PLANT, B_TREE, B_SPECTRAL, B_GEOMETRIC, \
    B_GELATINOUS, B_ORB, B_AVIAN, B_WINGED_MAN, B_SEMI_BIPEDAL, B_FLAT, B_GASTROPOD = range(1, 27)

# SIZE TYPES (exactly one of the following, 7=human sized) This list is ordered from small to large!
S_MICROSCOPIC, S_MINISCULE, S_TINY, S_VERY_SMALL, S_SMALL, S_SOMEWHAT_SMALL, S_HUMAN_SIZED, \
    S_SOMEWHAT_LARGE, S_LARGE, S_HUGE, S_GIGANTIC, S_VAST = range(1, 13)

sizes = {
    S_MICROSCOPIC: "microscopic",
    S_MINISCULE: "miniscule",
    S_TINY: "tiny",
    S_VERY_SMALL: "very small",
    S_SMALL: "small",
    S_SOMEWHAT_SMALL: "somewhat small",
    S_HUMAN_SIZED: "human sized",
    S_SOMEWHAT_LARGE: "somewhat large",
    S_LARGE: "large",
    S_HUGE: "huge",
    S_GIGANTIC: "gigantic",
    S_VAST: "vast"
}

bodytypes = {
    B_HUMANOID: "humanoid",
    B_QUADRUPED: "quadruped",
    B_BIPED: "biped",
    B_CHIROPTEROID: "chiropteroid",
    B_INSECTOID: "insectoid",
    B_TENTACLED: "tentacled",
    B_ARTHROPOD: "arthropod",
    B_CRUSTACEAN: "crustacean",
    B_PINNIPED: "pinniped",
    B_CETACEAN: "cetacean",
    B_FISH: "fish",
    B_OCTOPOID: "octopoid",
    B_NEBULOUS: "nebulous",
    B_CHIMAERA: "chimaera",
    B_SNAKE: "snake",
    B_PLANT: "plant",
    B_TREE: "tree",
    B_SPECTRAL: "spectral",
    B_GEOMETRIC: "geometric",
    B_GELATINOUS: "gelatinous",
    B_ORB: "orb",
    B_AVIAN: "avian",
    B_WINGED_MAN: "winged man",
    B_SEMI_BIPEDAL: "semi bipedal",
    B_FLAT: "flat",
    B_GASTROPOD: "gastropod"
}

# mass is in KG.
# stats are (stat, stat_class).
# stat_class means: the typical priority this stat is for a certain race (1..5)
# stat_class 1 means it is the most important stat for that race, and that stat may
# get an increase at every level. stat_class 5 means low importance and may get an
# increase every 5 levels only.
# stat types: AGIlity, CHArisma, INTelligence, LuCK, SPeeD, STAmina, STRength, WISdom. PSIonic
races = {
 'amphibian': {'bodytype': B_QUADRUPED,
               'language': 'Batrachian',
               'mass': 0.4,
               'size': S_VERY_SMALL,
               'stats': {'agi': (10, 4),
                         'cha': (10, 4),
                         'int': (1, 3),
                         'lck': (21, 3),
                         'spd': (1, 5),
                         'sta': (21, 3),
                         'str': (1, 5),
                         'wis': (43, 1)}},
 'android': {'bodytype': B_HUMANOID,
             'language': 'English',
             'mass': 120.0,
             'size': S_HUMAN_SIZED,
             'stats': {'agi': (50, 3),
                       'cha': (50, 2),
                       'int': (50, 1),
                       'lck': (10, 3),
                       'spd': (50, 3),
                       'sta': (50, 4),
                       'str': (50, 4),
                       'wis': (50, 3)}},
 'ape': {'bodytype': B_SEMI_BIPEDAL,
         'language': 'Ur',
         'mass': 120.0,
         'size': S_LARGE,
         'stats': {'agi': (30, 5),
                   'cha': (5, 3),
                   'int': (15, 3),
                   'lck': (10, 4),
                   'spd': (30, 5),
                   'sta': (43, 1),
                   'str': (43, 1),
                   'wis': (1, 2)}},
 'arachnid': {'bodytype': B_INSECTOID,
              'language': 'Arachnid',
              'mass': 0.2,
              'size': S_TINY,
              'stats': {'agi': (43, 1),
                        'cha': (1, 5),
                        'int': (1, 3),
                        'lck': (21, 3),
                        'spd': (31, 2),
                        'sta': (1, 5),
                        'str': (10, 4),
                        'wis': (1, 5)}},
 'artrell': {'bodytype': B_INSECTOID,
             'language': 'Artrexcian',
             'mass': 48.0,
             'size': S_SOMEWHAT_SMALL,
             'stats': {'agi': (50, 1),
                       'cha': (0, 4),
                       'int': (10, 4),
                       'lck': (33, 3),
                       'spd': (40, 2),
                       'sta': (10, 3),
                       'str': (10, 3),
                       'wis': (5, 5)}},
 'avidryl': {'bodytype': B_WINGED_MAN,
             'language': 'Avidryl',
             'mass': 60.0,
             'size': S_HUMAN_SIZED,
             'stats': {'agi': (50, 1),
                       'cha': (20, 3),
                       'int': (15, 4),
                       'lck': (2, 5),
                       'spd': (20, 3),
                       'sta': (20, 2),
                       'str': (40, 2),
                       'wis': (10, 5)}},
 'balrog': {'bodytype': B_WINGED_MAN,
            'language': 'Balrog',
            'mass': 1200.0,
            'size': S_GIGANTIC,
            'stats': {'agi': (40, 1),
                      'cha': (1, 5),
                      'int': (30, 2),
                      'lck': (20, 3),
                      'spd': (30, 2),
                      'sta': (40, 1),
                      'str': (30, 3),
                      'wis': (10, 3)}},
 'bat': {'bodytype': B_CHIROPTEROID,
         'language': 'Murcielago',
         'mass': 0.4,
         'size': S_VERY_SMALL,
         'stats': {'agi': (10, 2),
                   'cha': (11, 3),
                   'int': (1, 3),
                   'lck': (24, 3),
                   'spd': (52, 3),
                   'sta': (65, 1),
                   'str': (13, 4),
                   'wis': (10, 5)}},
 'bear': {'bodytype': B_SEMI_BIPEDAL,
          'language': 'Ursine',
          'mass': 160.0,
          'size': S_LARGE,
          'stats': {'agi': (1, 5),
                    'cha': (21, 3),
                    'int': (15, 3),
                    'lck': (10, 4),
                    'spd': (1, 5),
                    'sta': (43, 1),
                    'str': (43, 1),
                    'wis': (31, 2)}},
 'bird': {'bodytype': B_AVIAN,
          'language': 'Avian',
          'mass': 0.4,
          'size': S_VERY_SMALL,
          'stats': {'agi': (43, 1),
                    'cha': (31, 2),
                    'int': (1, 5),
                    'lck': (21, 3),
                    'spd': (43, 1),
                    'sta': (1, 5),
                    'str': (10, 4),
                    'wis': (10, 4)}},
 'blob': {'bodytype': B_SNAKE,
          'language': 'creosote',
          'mass': 1.6,
          'size': S_SMALL,
          'stats': {'agi': (1, 5),
                    'cha': (1, 5),
                    'int': (1, 5),
                    'lck': (1, 5),
                    'spd': (1, 5),
                    'sta': (1, 5),
                    'str': (1, 5),
                    'wis': (1, 5)}},
 'bot': {'bodytype': B_ORB,
         'language': 'Bocce',
         'mass': 40.0,
         'size': S_SOMEWHAT_SMALL,
         'stats': {'agi': (50, 3),
                   'cha': (50, 2),
                   'int': (50, 1),
                   'lck': (10, 3),
                   'spd': (50, 3),
                   'sta': (50, 4),
                   'str': (50, 4),
                   'wis': (50, 3)}},
 'bugbear': {'bodytype': B_SEMI_BIPEDAL,
             'language': 'Insectursine',
             'mass': 18.0,
             'size': S_LARGE,
             'stats': {'agi': (1, 5),
                       'cha': (21, 3),
                       'int': (21, 3),
                       'lck': (10, 4),
                       'spd': (1, 5),
                       'sta': (43, 1),
                       'str': (43, 1),
                       'ugliness': (91, 3),
                       'wis': (31, 2)}},
 'cat': {'bodytype': B_QUADRUPED,
         'language': 'Feline',
         'mass': 4.0,
         'size': S_SMALL,
         'stats': {'agi': (43, 1),
                   'cha': (43, 1),
                   'int': (1, 5),
                   'lck': (43, 1),
                   'spd': (31, 2),
                   'sta': (10, 4),
                   'str': (10, 4),
                   'wis': (10, 4)}},
 'centaur': {'bodytype': B_SEMI_BIPEDAL,
             'language': 'Centaurian',
             'mass': 120.0,
             'size': S_LARGE,
             'stats': {'agi': (21, 3),
                       'cha': (21, 3),
                       'int': (21, 3),
                       'lck': (43, 1),
                       'spd': (31, 2),
                       'sta': (43, 1),
                       'str': (31, 2),
                       'wis': (31, 2)}},
 'chimera': {'bodytype': B_CHIMAERA,
             'language': 'Chimerole',
             'mass': 20.0,
             'size': S_LARGE,
             'stats': {'agi': (31, 2),
                       'cha': (1, 5),
                       'int': (21, 3),
                       'lck': (10, 4),
                       'spd': (43, 1),
                       'sta': (31, 2),
                       'str': (21, 3),
                       'wis': (21, 3)}},
 'cow': {'bodytype': B_QUADRUPED,
         'language': 'Bovine',
         'mass': 160.0,
         'size': S_LARGE,
         'stats': {'agi': (1, 5),
                   'cha': (10, 4),
                   'int': (1, 5),
                   'lck': (1, 5),
                   'spd': (1, 5),
                   'sta': (43, 1),
                   'str': (31, 2),
                   'wis': (1, 5)}},
 'dark-elf': {'bodytype': B_HUMANOID,
              'language': 'Edhellen',
              'mass': 60.0,
              'size': S_HUMAN_SIZED,
              'stats': {'agi': (40, 3),
                        'cha': (35, 2),
                        'int': (65, 1),
                        'lck': (50, 1),
                        'spd': (40, 3),
                        'sta': (30, 3),
                        'strenght': (25, 4),
                        'wis': (60, 1)}},
 'deer': {'bodytype': B_QUADRUPED,
          'language': 'Tier',
          'mass': 120.0,
          'size': S_HUMAN_SIZED,
          'stats': {'agi': (21, 3),
                    'cha': (21, 3),
                    'int': (1, 5),
                    'lck': (10, 4),
                    'spd': (31, 2),
                    'sta': (31, 2),
                    'str': (43, 1),
                    'wis': (1, 5)}},
 'demi-god': {'bodytype': B_HUMANOID,
              'language': 'Sublime',
              'mass': 80.0,
              'size': S_HUMAN_SIZED,
              'stats': {'agi': (31, 2),
                        'cha': (31, 2),
                        'int': (31, 2),
                        'lck': (43, 1),
                        'spd': (43, 1),
                        'sta': (31, 2),
                        'str': (31, 2),
                        'wis': (31, 2)}},
 'demon': {'bodytype': B_WINGED_MAN,
           'language': 'Demoniac',
           'mass': 10.0,
           'size': S_SOMEWHAT_LARGE,
           'stats': {'agi': (31, 2),
                     'cha': (31, 2),
                     'int': (31, 2),
                     'lck': (43, 1),
                     'psi': (50, 2),
                     'spd': (31, 2),
                     'sta': (31, 2),
                     'str': (31, 2),
                     'wis': (10, 4)}},
 'dog': {'bodytype': B_QUADRUPED,
         'language': 'Canine',
         'mass': 20.0,
         'size': S_SOMEWHAT_SMALL,
         'stats': {'agi': (21, 3),
                   'cha': (31, 2),
                   'int': (10, 4),
                   'lck': (10, 4),
                   'spd': (21, 3),
                   'sta': (21, 3),
                   'str': (21, 3),
                   'wis': (1, 5)}},
 'dragon': {'bodytype': B_SEMI_BIPEDAL,
            'language': 'Dragonate',
            'mass': 1600.0,
            'size': S_HUGE,
            'stats': {'agi': (43, 1),
                      'cha': (31, 2),
                      'int': (31, 2),
                      'lck': (43, 1),
                      'spd': (21, 3),
                      'sta': (43, 1),
                      'str': (43, 1),
                      'wis': (43, 1)}},
 'dryad': {'bodytype': B_HUMANOID,
           'language': 'Vadinho',
           'mass': 4.0,
           'size': S_SMALL,
           'stats': {'agi': (31, 2),
                     'cha': (43, 1),
                     'int': (10, 4),
                     'lck': (31, 2),
                     'spd': (31, 2),
                     'sta': (1, 5),
                     'str': (10, 4),
                     'wis': (31, 2)}},
 'dummy': {'bodytype': B_HUMANOID,
           'language': 'Common',
           'mass': 200.0,
           'size': S_LARGE,
           'stats': {'agi': (1, 1),
                     'cha': (1, 1),
                     'int': (1, 1),
                     'lck': (1, 1),
                     'spd': (1, 1),
                     'sta': (1, 1),
                     'str': (1, 1),
                     'wis': (1, 1)}},
 'dwarf': {'bodytype': B_HUMANOID,
           'language': 'Malkierien',
           'mass': 8.0,
           'size': S_SOMEWHAT_SMALL,
           'stats': {'agi': (10, 2),
                     'cha': (11, 3),
                     'int': (18, 3),
                     'lck': (60, 1),
                     'spd': (20, 3),
                     'sta': (60, 1),
                     'str': (40, 1),
                     'wis': (20, 3)}},
 'elemental': {'bodytype': B_NEBULOUS,
               'language': 'Periodict',
               'mass': 1600.0,
               'size': S_LARGE,
               'stats': {'agi': (21, 3),
                         'cha': (21, 3),
                         'int': (21, 3),
                         'lck': (21, 3),
                         'spd': (21, 3),
                         'sta': (21, 3),
                         'str': (21, 3),
                         'wis': (21, 3)}},
 'elephant': {'bodytype': B_QUADRUPED,
              'language': 'Pachydermian',
              'mass': 1600.0,
              'size': S_HUGE,
              'stats': {'agi': (1, 5),
                        'cha': (10, 4),
                        'int': (10, 4),
                        'lck': (21, 3),
                        'spd': (10, 4),
                        'sta': (43, 1),
                        'str': (43, 1),
                        'wis': (43, 1)}},
 'elf': {'bodytype': B_HUMANOID,
         'language': 'Edhellen',
         'mass': 60.0,
         'size': S_HUMAN_SIZED,
         'stats': {'agi': (40, 3),
                   'cha': (40, 1),
                   'int': (50, 1),
                   'lck': (50, 1),
                   'spd': (40, 3),
                   'sta': (20, 4),
                   'str': (15, 5),
                   'wis': (50, 1)}},
 'faerie': {'bodytype': B_WINGED_MAN,
            'language': 'Elcharean',
            'mass': 0.2,
            'size': S_TINY,
            'stats': {'agi': (60, 1),
                      'cha': (30, 3),
                      'int': (10, 2),
                      'lck': (30, 2),
                      'spd': (40, 2),
                      'sta': (10, 5),
                      'str': (5, 5),
                      'wis': (15, 2)}},
 'fish': {'bodytype': B_FISH,
          'language': 'Ichthine',
          'mass': 8.0,
          'size': S_SMALL,
          'stats': {'agi': (31, 2),
                    'cha': (1, 5),
                    'int': (1, 5),
                    'lck': (1, 5),
                    'spd': (21, 3),
                    'sta': (10, 4),
                    'str': (10, 4),
                    'wis': (21, 3)}},
 'gargoyle': {'bodytype': B_WINGED_MAN,
              'language': 'Gargoyleish',
              'mass': 120.0,
              'size': S_SOMEWHAT_SMALL,
              'stats': {'agi': (1, 5),
                        'cha': (1, 5),
                        'int': (10, 4),
                        'lck': (10, 4),
                        'spd': (10, 4),
                        'sta': (43, 1),
                        'str': (43, 1),
                        'wis': (31, 2)}},
 'giant': {'bodytype': B_HUMANOID,
           'language': 'Loyavenku',
           'mass': 1600.0,
           'size': S_HUGE,
           'stats': {'agi': (2, 5),
                     'cha': (10, 4),
                     'int': (10, 3),
                     'lck': (5, 4),
                     'spd': (1, 5),
                     'sta': (70, 1),
                     'str': (80, 1),
                     'wis': (1, 5)}},
 'gnoll': {'bodytype': B_HUMANOID,
           'language': 'Kaydoch',
           'mass': 48.0,
           'size': S_SOMEWHAT_SMALL,
           'stats': {'agi': (31, 2),
                     'cha': (1, 5),
                     'int': (10, 4),
                     'lck': (31, 2),
                     'spd': (21, 3),
                     'sta': (21, 3),
                     'str': (21, 3),
                     'wis': (10, 4)}},
 'gnome': {'bodytype': B_HUMANOID,
           'language': 'Kaydiyee',
           'mass': 0.4,
           'size': S_VERY_SMALL,
           'stats': {'agi': (20, 3),
                     'cha': (1, 5),
                     'int': (50, 1),
                     'lck': (40, 2),
                     'spd': (20, 2),
                     'sta': (10, 4),
                     'str': (30, 3),
                     'wis': (40, 1)}},
 'goblin': {'bodytype': B_HUMANOID,
            'language': 'Goblinish',
            'mass': 72.0,
            'size': S_HUMAN_SIZED,
            'stats': {'agi': (43, 1),
                      'cha': (1, 5),
                      'int': (10, 4),
                      'lck': (10, 4),
                      'spd': (31, 2),
                      'sta': (43, 1),
                      'str': (21, 3),
                      'wis': (21, 3)}},
 'god': {'bodytype': B_NEBULOUS,
         'language': 'Divine',
         'mass': 0.0,
         'size': S_LARGE,
         'stats': {'agi': (43, 1),
                   'cha': (43, 1),
                   'int': (43, 1),
                   'lck': (43, 1),
                   'spd': (43, 1),
                   'sta': (43, 1),
                   'str': (43, 1),
                   'wis': (43, 1)}},
 'golem': {'bodytype': B_HUMANOID,
           'language': 'Emet',
           'mass': 200.0,
           'size': S_LARGE,
           'stats': {'agi': (21, 3),
                     'cha': (1, 5),
                     'int': (10, 4),
                     'lck': (1, 5),
                     'spd': (21, 3),
                     'sta': (31, 2),
                     'str': (43, 1),
                     'wis': (31, 2)}},
 'griffin': {'bodytype': B_SEMI_BIPEDAL,
             'language': 'Griffinish',
             'mass': 120.0,
             'size': S_LARGE,
             'stats': {'agi': (31, 2),
                       'cha': (1, 5),
                       'int': (1, 5),
                       'lck': (43, 1),
                       'spd': (31, 2),
                       'sta': (43, 1),
                       'str': (43, 1),
                       'wis': (10, 4)}},
 'half-elf': {'bodytype': B_HUMANOID,
              'language': 'Edhellen',
              'mass': 60.0,
              'size': S_HUMAN_SIZED,
              'stats': {'agi': (30, 2),
                        'cha': (30, 3),
                        'int': (30, 1),
                        'lck': (30, 4),
                        'spd': (60, 1),
                        'sta': (30, 5),
                        'str': (15, 3),
                        'wis': (30, 2)}},
 'half-orc': {'bodytype': B_HUMANOID,
              'language': 'Tangetto',
              'mass': 80.0,
              'size': S_HUMAN_SIZED,
              'stats': {'agi': (2, 1),
                        'cha': (4, 5),
                        'int': (20, 2),
                        'lck': (1, 5),
                        'spd': (70, 1),
                        'sta': (40, 2),
                        'str': (20, 2),
                        'wis': (10, 5)}},
 'halfling': {'bodytype': B_HUMANOID,
              'language': 'Duuk',
              'mass': 20.0,
              'size': S_SMALL,
              'stats': {'agi': (40, 2),
                        'cha': (80, 2),
                        'int': (20, 2),
                        'lck': (80, 2),
                        'spd': (30, 1),
                        'sta': (10, 3),
                        'str': (10, 3),
                        'wis': (10, 4)}},
 'hobbit': {'bodytype': B_HUMANOID,
            'language': 'Hoboken',
            'mass': 20.0,
            'size': S_SMALL,
            'stats': {'agi': (20, 1),
                      'cha': (33, 3),
                      'int': (20, 2),
                      'lck': (80, 1),
                      'spd': (30, 2),
                      'sta': (20, 2),
                      'str': (10, 4),
                      'wis': (20, 3)}},
 'horse': {'bodytype': B_QUADRUPED,
           'language': 'Equine',
           'mass': 240.0,
           'size': S_LARGE,
           'stats': {'agi': (31, 2),
                     'cha': (21, 3),
                     'int': (1, 5),
                     'lck': (1, 5),
                     'spd': (31, 2),
                     'sta': (31, 2),
                     'str': (73, 1),
                     'wis': (1, 5)}},
 'human': {'bodytype': B_HUMANOID,
           'language': 'English',
           'mass': 72.0,
           'size': S_HUMAN_SIZED,
           'stats': {'agi': (33, 3),
                     'cha': (33, 2),
                     'int': (40, 1),
                     'lck': (20, 3),
                     'spd': (30, 3),
                     'sta': (30, 4),
                     'str': (20, 3),
                     'wis': (40, 3)}},
 'insect': {'bodytype': B_INSECTOID,
            'language': 'Insectoid',
            'mass': 0.04,
            'size': S_MINISCULE,
            'stats': {'agi': (31, 2),
                      'cha': (1, 5),
                      'int': (1, 5),
                      'lck': (43, 1),
                      'spd': (43, 1),
                      'sta': (1, 5),
                      'str': (1, 5),
                      'wis': (1, 5)}},
 'kender': {'bodytype': B_HUMANOID,
            'language': 'Kendrall',
            'mass': 32.0,
            'size': S_SOMEWHAT_SMALL,
            'stats': {'agi': (40, 3),
                      'cha': (40, 2),
                      'int': (20, 2),
                      'lck': (33, 3),
                      'spd': (50, 1),
                      'sta': (20, 1),
                      'str': (3, 5),
                      'wis': (7, 4)}},
 'klingon': {'bodytype': B_HUMANOID,
             'language': 'Tlhinghan',
             'mass': 100.0,
             'size': S_SOMEWHAT_LARGE,
             'stats': {'agi': (30, 2),
                       'cha': (10, 5),
                       'int': (25, 2),
                       'lck': (1, 4),
                       'spd': (30, 3),
                       'sta': (60, 1),
                       'str': (60, 1),
                       'wis': (1, 5)}},
 'kobold': {'bodytype': B_HUMANOID,
            'language': 'Yeik',
            'mass': 52.0,
            'size': S_SOMEWHAT_SMALL,
            'stats': {'agi': (21, 3),
                      'cha': (10, 4),
                      'int': (10, 4),
                      'lck': (21, 3),
                      'spd': (21, 3),
                      'sta': (43, 1),
                      'str': (43, 1),
                      'wis': (10, 4)}},
 'lizard': {'bodytype': B_QUADRUPED,
            'language': 'Reptilian',
            'mass': 0.4,
            'size': S_VERY_SMALL,
            'stats': {'agi': (21, 3),
                      'cha': (10, 4),
                      'int': (1, 5),
                      'lck': (10, 4),
                      'spd': (21, 3),
                      'sta': (21, 3),
                      'str': (21, 3),
                      'wis': (1, 5)}},
 'mech': {'bodytype': B_HUMANOID,
          'language': 'English',
          'mass': 400.0,
          'size': S_HUGE,
          'stats': {'agi': (50, 3),
                    'cha': (50, 2),
                    'int': (1, 1),
                    'lck': (10, 3),
                    'spd': (50, 3),
                    'sta': (50, 4),
                    'str': (90, 4),
                    'wis': (1, 3)}},
 'nymph': {'bodytype': B_HUMANOID,
           'language': 'Nymal',
           'mass': 5.6,
           'size': S_SOMEWHAT_SMALL,
           'stats': {'agi': (50, 1),
                     'cha': (80, 1),
                     'int': (25, 4),
                     'lck': (50, 2),
                     'spd': (60, 2),
                     'sta': (7, 5),
                     'str': (3, 5),
                     'wis': (20, 4)}},
 'ogre': {'bodytype': B_HUMANOID,
          'language': 'Shangtai',
          'mass': 160.0,
          'size': S_LARGE,
          'stats': {'agi': (1, 5),
                    'cha': (1, 5),
                    'int': (10, 4),
                    'lck': (1, 5),
                    'spd': (7, 4),
                    'sta': (68, 1),
                    'str': (50, 1),
                    'wis': (1, 5)}},
 'orc': {'bodytype': B_HUMANOID,
         'language': 'Tangetto',
         'mass': 88.0,
         'size': S_SOMEWHAT_LARGE,
         'stats': {'agi': (10, 2),
                   'cha': (1, 5),
                   'int': (10, 3),
                   'lck': (3, 4),
                   'spd': (40, 2),
                   'sta': (30, 2),
                   'str': (35, 1),
                   'wis': (3, 5)}},
 'pegasus': {'bodytype': B_QUADRUPED,
             'language': 'Voloquine',
             'mass': 120.0,
             'size': S_LARGE,
             'stats': {'agi': (43, 1),
                       'cha': (43, 1),
                       'int': (21, 3),
                       'lck': (43, 1),
                       'spd': (31, 2),
                       'sta': (31, 2),
                       'str': (31, 2),
                       'wis': (31, 2)}},
 'pig': {'bodytype': B_QUADRUPED,
         'language': 'Porcine',
         'mass': 60.0,
         'size': S_SOMEWHAT_SMALL,
         'stats': {'agi': (1, 5),
                   'cha': (1, 5),
                   'int': (15, 2),
                   'lck': (1, 5),
                   'spd': (10, 4),
                   'sta': (43, 1),
                   'str': (21, 3),
                   'wis': (31, 2)}},
 'plant': {'bodytype': B_PLANT,
           'language': 'Vegetal',
           'mass': 0.4,
           'size': S_VERY_SMALL,
           'stats': {'agi': (1, 5),
                     'cha': (11, 3),
                     'int': (1, 5),
                     'lck': (21, 3),
                     'spd': (1, 5),
                     'sta': (21, 3),
                     'str': (21, 3),
                     'wis': (1, 5)}},
 'primate': {'bodytype': B_SEMI_BIPEDAL,
             'language': 'Proto',
             'mass': 60.0,
             'size': S_SMALL,
             'stats': {'agi': (21, 3),
                       'cha': (15, 3),
                       'int': (21, 3),
                       'lck': (21, 3),
                       'spd': (21, 3),
                       'sta': (10, 4),
                       'str': (10, 4),
                       'wis': (10, 4)}},
 'replicant': {'bodytype': B_HUMANOID,
               'language': 'English',
               'mass': 72.0,
               'size': S_HUMAN_SIZED,
               'stats': {'agi': (40, 3),
                         'cha': (40, 2),
                         'int': (10, 1),
                         'lck': (1, 3),
                         'spd': (40, 3),
                         'sta': (40, 4),
                         'str': (40, 4),
                         'wis': (1, 3)}},
 'rodent': {'bodytype': B_QUADRUPED,
            'language': 'Rodentian',
            'mass': 0.4,
            'size': S_VERY_SMALL,
            'stats': {'agi': (21, 3),
                      'cha': (1, 5),
                      'int': (1, 5),
                      'lck': (1, 5),
                      'spd': (31, 2),
                      'sta': (10, 4),
                      'str': (1, 5),
                      'wis': (10, 4)}},
 'satyr': {'bodytype': B_HUMANOID,
           'language': 'Wulinaxian',
           'mass': 6.0,
           'size': S_HUMAN_SIZED,
           'stats': {'agi': (50, 2),
                     'cha': (3, 5),
                     'int': (33, 3),
                     'lck': (10, 1),
                     'spd': (5, 2),
                     'sta': (25, 2),
                     'str': (2, 4),
                     'wis': (80, 1)}},
 'sheep': {'bodytype': B_QUADRUPED,
           'language': 'Ovine',
           'mass': 40.0,
           'size': S_SOMEWHAT_SMALL,
           'stats': {'agi': (21, 3),
                     'cha': (21, 3),
                     'int': (1, 5),
                     'lck': (1, 5),
                     'spd': (10, 4),
                     'sta': (21, 3),
                     'str': (21, 3),
                     'wis': (1, 5)}},
 'slug': {'bodytype': B_GASTROPOD,
          'language': 'Clavering',
          'mass': 0.12,
          'size': S_VERY_SMALL,
          'stats': {'agi': (1, 5),
                    'cha': (1, 5),
                    'int': (1, 5),
                    'lck': (1, 5),
                    'spd': (1, 5),
                    'sta': (1, 5),
                    'str': (10, 4),
                    'wis': (10, 4)}},
 'snake': {'bodytype': B_SNAKE,
           'language': 'Herpetian',
           'mass': 1.6,
           'size': S_SMALL,
           'stats': {'agi': (10, 4),
                     'cha': (1, 5),
                     'int': (10, 4),
                     'lck': (43, 1),
                     'spd': (10, 4),
                     'sta': (10, 4),
                     'str': (1, 5),
                     'wis': (31, 2)}},
 'strider': {'bodytype': B_HUMANOID,
             'language': 'English',
             'mass': 400.0,
             'size': S_HUGE,
             'stats': {'agi': (50, 1),
                       'cha': (1, 3),
                       'int': (1, 3),
                       'lck': (10, 3),
                       'spd': (90, 1),
                       'sta': (50, 4),
                       'str': (90, 1),
                       'wis': (1, 3)}},
 'tortoise': {'bodytype': B_QUADRUPED,
              'language': 'Tortois',
              'mass': 3.6,
              'size': S_SMALL,
              'stats': {'agi': (10, 4),
                        'cha': (10, 4),
                        'int': (21, 3),
                        'lck': (21, 3),
                        'spd': (1, 5),
                        'sta': (43, 1),
                        'str': (1, 5),
                        'wis': (43, 1)}},
 'tree': {'bodytype': B_TREE,
          'language': 'Entish',
          'mass': 160.0,
          'size': S_LARGE,
          'stats': {'agi': (1, 5),
                    'cha': (21, 3),
                    'int': (1, 5),
                    'lck': (43, 1),
                    'spd': (1, 5),
                    'sta': (43, 1),
                    'str': (21, 3),
                    'wis': (10, 4)}},
 'troll': {'bodytype': B_HUMANOID,
           'language': 'Murdoch',
           'mass': 8.0,
           'size': S_HUMAN_SIZED,
           'stats': {'agi': (10, 2),
                     'cha': (11, 3),
                     'int': (11, 3),
                     'lck': (15, 4),
                     'spd': (20, 3),
                     'sta': (65, 1),
                     'str': (50, 1),
                     'wis': (5, 5)}},
 'unicorn': {'bodytype': B_QUADRUPED,
             'language': 'Cornequine',
             'mass': 160.0,
             'size': S_LARGE,
             'stats': {'agi': (31, 2),
                       'cha': (90, 5),
                       'int': (10, 4),
                       'lck': (43, 1),
                       'spd': (21, 3),
                       'sta': (21, 3),
                       'str': (21, 3),
                       'wis': (31, 2)}},
 'vehicle': {'bodytype': B_ORB,
             'language': 'Bocce',
             'mass': 40.0,
             'size': S_LARGE,
             'stats': {'agi': (50, 3),
                       'cha': (50, 2),
                       'int': (1, 1),
                       'lck': (10, 3),
                       'spd': (50, 3),
                       'sta': (50, 4),
                       'str': (50, 4),
                       'wis': (1, 3)}},
 'viper': {'bodytype': B_SNAKE,
           'language': 'Aspish',
           'mass': 1.2,
           'size': S_SMALL,
           'stats': {'agi': (10, 4),     # AGI, CHA, INT, LCK, SPD, STA, STR, WIS
                     'cha': (1, 5),
                     'int': (10, 4),
                     'lck': (43, 1),
                     'spd': (10, 4),
                     'sta': (10, 4),
                     'str': (1, 5),
                     'wis': (31, 2)}},
 'vulcan': {'bodytype': B_HUMANOID,
            'language': 'Vulcan',
            'mass': 60.0,
            'size': S_HUMAN_SIZED,
            'stats': {'agi': (30, 2),
                      'cha': (1, 5),
                      'int': (70, 1),
                      'lck': (1, 1),
                      'psi': (20, 1),
                      'spd': (30, 3),
                      'sta': (30, 1),
                      'str': (30, 5),
                      'wis': (60, 1)}},
 'wraith': {'bodytype': B_SPECTRAL,
            'language': 'Revenant',
            'mass': 4.0,
            'size': S_SOMEWHAT_LARGE,
            'stats': {'agi': (31, 2),
                      'cha': (1, 5),
                      'int': (10, 4),
                      'lck': (43, 1),
                      'spd': (21, 3),
                      'sta': (21, 3),
                      'str': (21, 3),
                      'wis': (31, 2)}}
}
