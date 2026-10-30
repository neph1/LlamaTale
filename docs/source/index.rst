
Tale |version| - MUD, mudlib & Interactive Fiction framework (project is frozen)
********************************************************************************

.. image:: _static/tale-large.png
    :align: center
    :alt: Tale logo

*************
What is Tale?
*************

It is a library for building `Interactive Fiction <http://en.wikipedia.org/wiki/Interactive_fiction>`_,
mudlibs and `muds <http://en.wikipedia.org/wiki/MUD>`_ in Python.

It is some sort of cross-breed between LPMud, CircleMud/DikuMud, and Infocom™ Z-machine.

Tale requires Python 3.5 or newer.
(If you have an older version of Python, stick to Tale 2.8 or older, which still supports Python 2.7 as well)

You can run Tale in console mode, where it is a pure text interface running in your
console window. Or you can run Tale in your web browser.

.. note::
    The multi-user aspects are fairly new and still somewhat incomplete.
    Until recently, the focus has been on the (single player) interactive fiction things.
    However if my server is up, you can find running MUD instances here: http://www.razorvine.net/tale/
    and here: http://www.razorvine.net/circle/

.. note::
    This documentation is still a stub. I hope to write some real documentation soon,
    but in the meantime, use the source, Luke.

Tale can be found on Pypi as `tale <http://pypi.python.org/pypi/tale/>`_.
The source is on Github: https://github.com/irmen/Tale


Getting started
---------------
Install tale, preferably using ``pip install tale``. You can also download the source, and then execute ``python setup.py install``.

Tale requires the  `appdirs <http://pypi.python.org/pypi/appdirs/>`_ library to sensibly store data files such as savegames.

It requires the  `smartypants <http://pypi.python.org/pypi/smartypants/>`_ library to print out nicely formatted quotes and dashes.

It requires the  `colorama <http://pypi.python.org/pypi/colorama/>`_ library to print out text accents (bold, bright, underlined, reversevideo etc).

It requires the `serpent <http://pypi.python.org/pypi/serpent/>`_ library to be able to save and load game data (savegames).

(All of these libraries should be installed automatically if you use pip to install tale itself)

Optionally, you can install the `prompt_toolkit <https://pypi.python.org/pypi/prompt_toolkit/>`_ library for a nicer console text interface experience,
but this one is not strictly required to be able to run.

After all that, you'll need a story to run it on (tale by itself doesn't do anything,
it's only a framework to build games with).
There's a tiny demo embedded in the library itself, you can start that with::

    python -m tale.demo.story

You can add several command line options:
 * ``--web`` add this to get a web browser interface
 * ``--mud`` add this to launch the demo game as mud (multi-user) server

Fool around with your pet and try to get out of the house. There's a larger demo story included in the source distribution,
in the ``stories`` directory. But you will have to download and extract the source distribution manually to get it.

Start the demo story using one of the supplied start scripts. You don't have to install Tale first, the script can figure it out.

You can also start it without the script and by using the tale driver directly, but then
it is recommended to properly install tale first. This method of launching stories
won't work from the distribution's root directory itself.

Anyway, the command to do so is::

    $ python -m tale.main --game <path-to-the-story/demo-directory>`

    # or, with the installed launcher script:
    $ tale-run --game <path-to-the-story/demo-directory>`

You can use the ``--help`` argument to see some help about this command.
You can use ``--web`` to start the browser version of the interface rather than the text console version.
There are some other command line arguments such as ``--mode`` that allow you to select other things, look at the help
output to learn more.

The story might prompt you with a couple of questions:
Choose not to load a saved game (you will have none at first start anyway).
Choose to create a default player character or build a custom one. If you choose *wizard privileges*, you
gain access to a whole lot of special wizard commands that can be used to tinker with the internals of the game.

Type :kbd:`help` and :kbd:`help soul` to get an idea of the stuff you can type at the prompt.

You may want to go to the Town Square and say hello to the people standing there::

    >> look

      [Town square]
      The old town square of the village.  It is not much really, and narrow
      streets quickly lead away from the small fountain in the center.
      There's an alley to the south.  A long straight lane leads north towards
      the horizon.
      You see a black gem, a blue gem, a bag, a box1 (a black box), a box2 (a
      white box), a clock, a newspaper, and a trashcan.  Laish the town crier,
      ant, blubbering idiot, and rat are here.

    >> greet laish and the idiot

      You greet Laish the town crier and blubbering idiot.  Laish the town
      crier says: "Hello there, Irmen."  Blubbering idiot drools on you.

    >> recoil

      You recoil with fear.

    >>

Features
--------

A random list of the features of the current codebase:

- requires Python 3.5 or newer
- game engine and framework code is separated from the actual game code
- single-player Interactive Fiction mode and multi-player MUD mode
- selectable interface types: text console interface, or web browser interface
- MUD mode runs as a web server (no old-skool console access via telnet or ssh for now)
- can load and run games/stories directly from a zipfile or from extracted folders.
- wizard and normal player privileges, wizards gain access to a set of special 'debug' commands that are helpful
  while testing/debugging/administrating the game.
- the parser uses a soul based on the classic LPC-MUD's 'soul.c' from the late 90's
- the soul has 250+ 'emotes' such as 'bounce', 'shrug' and 'ponder'.
- it knows 2200+ adverbs that you can use with these emotes. It does prefix matching so you don't have to type
  it out in full (gives a list of suggestions if multiple words match).
- it knows about bodyparts that you can target certain actions (such as kick or pat) at.
- it can deal with object names that consist of multiple words (i.e. contain spaces). For instance, it understands
  when you type 'get the blue pill' when there are multiple pills on the table.
- tab-completion of commands on systems that support readline
- you can alter the meaning of a sentence by using words like fail, attempt, don't, suddenly, pretend
- you can put stuff into a bag and carry the bag, to avoid cluttering your inventory.
- you can refer to earlier used items and persons by using a pronoun ("examine box / drop it", "examine idiot / slap him").
- yelling something will actually be heard by creatures in adjacent locations. They'll get a message that
  someone is yelling something, and if possible, where the sound is coming from.
- text is nicely formatted when outputted (dynamically wrapped to a configurable width).
- uses ansi sequence to spice up the console output a bit (needs colorama on windows, falls back to plain text if not installed)
- uses smartypants to automatically render quotes, dashes, ellipsis in a nicer way.
- game can be saved (and reloaded)
- save game data is placed in the operating system's user data directory instead of some random location
- there's a list of 70+ creature races, adapted from the Dead Souls 2 mudlib
- supports two kinds of money: fantasy (gold/silver/copper) and modern (dollars). Text descriptions adapt to this.
- money can be given away, dropped on the floor, and picked up.
- it's possible for items to be combined into new items.
- game clock is independent of real-time wall clock, configurable speed and start time
- server 'tick' synced with command entry, or independent. This means things can happen in the background.
- there is a simple decorator that makes that a method gets invoked periodically, for asynchronous actions
- for more control you can make a 'deferred call' to schedule something to be called at a later time
- you can also quite easily schedule calls to be executed at a defined later moment in time
- using generators (yield statements) instead of regular input() calls,
  it is easy to create sequential dialogs (question-response) that will be handled without blocking the driver
  (the driver loop is not yet fully asynchronous but that may come in the future)
- easy definition of commands in separate functions, uses docstrings to define command help texts
- command function implementations are quite compact due to convenient parameters, and available methods on the game objects
- command code gets parse information from the soul parser as parameter; very little parsing needs to be done in the command code itself
- there's a large set of configurable parameters on a per-story basis
- stories can define their own introduction text and completion texts
- stories can define their own commands or override existing commands
- a lock/unlock/open/close door mechanism is provided with internal door codes to match keys (or key-like objects) against.
- action and event notification mechanism: objects are notified when things happen (such as the player entering a room, or someone saying a line of text) and can react on that.
- contains a simple virtual file system to provide easy resource loading / datafile storage.
- provides a simple pubsub/event signaling mechanism
- crashes are reported as detailed tracebacks showing local variable values per frame, to ease error reporting and debugging
- I/O abstraction layer to be able to create alternative interfaces to the engine
- for now, the game object model is object-oriented. You defined objects by instantiating prebuilt classes,
  or derive new classes from them with changed behavior. Currently this means that writing a game is
  very much a programming job. This may or may not improve in the future (to allow for more natural ways
  of writing a game story, in a DSL or whatever).
- a set of unit tests to validate a large part of the code


MUD mode versus Interactive Fiction mode
----------------------------------------
The Tale game driver launches in Interactive Fiction mode by default.

To run a story (or world, rather) in multi-user MUD mode, use the :kbd:`--mode mud` command line switch.
A whole lot of new commands and features are enabled when you do this
(amongst others: message-of-the-day support and the 'stats' command).
Running a IF story in MUD mode may cause some problems. Therefore you can
specify in the story config what game modes your story supports.


Copyright
---------

Tale is copyright © Irmen de Jong (irmen@razorvine.net | http://www.razorvine.net).
Since version 3.4, it's licensed under GNU LGPL v3, see https://www.gnu.org/licenses/lgpl-3.0.html
Versions older than that have a different license (GPL v3).


API documentation
-----------------

Preliminary (auto-generated) API documentation:

.. toctree::
   :caption: Contents of this manual:

   api.rst
