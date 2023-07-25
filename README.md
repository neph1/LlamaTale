This fork uses an LLM backend to describe things in a more vivid way. (LLM not included)

By default it uses KoboldCpp, but if you're feeling adventurous you can change llm_config.yaml in the tale/ folder to another one. 

2. Get and install KoboldCpp: https://github.com/LostRuins/koboldcpp/releases
3. Download a suitable llm model for koboldcpp. I recommend https://huggingface.co/TheBloke/Nous-Hermes-Llama2-GGML or https://huggingface.co/TheBloke/chronos-hermes-13B-GGML
4. Make sure KoboldCpp works.
1. Download repo, either with 'git clone' or as a zip.
6. Run 'pip install -r requirements.txt'
7. Start KoboldCpp (port 5001 by default)
8. Start with ``python -m stories.prancingllama.story``

In the game:
You can probably read up on this, or use 'help' in the prompt, but you can move around using directions, like n, w, s, e, or type the location you want to go to.
To trigger a dialogue, address people with 'say character: what you want to say'. There are a number of 'aliases' for each character, and the game seems to help you find the right one.

Features:
* When the MUD describes something, through commands like 'look' or other verbs, it sends the original description as a prompt to the LLM. The LLM either has free hands to write as much as it wants, or for some things, it's limited to a certain amount of tokens, not to cause too many delays.
* Not only for player-driven actions, mobs and NPC's also trigger this.
* It has a 'rolling memory' of previous generations, this is inserted before the instructions in the prompt with each request. This should help it keep the context.
* Characters have a short memory for conversations to keep them on track, as well.

Caveats:
* Like any LLM generated content, it's only as good as its input, and can sometimes go off-track when generating responses. Thus, the original description the MUD generates is also included, not to lose any important data.
* The LLM (currently) can't drive any actions. There's no parsing happening of the content it generates.
* It's written specifically for KoboldCpp as backend, but as much as possible of the config is in llm_config.yaml, so you can experiment with other backends as well.









ORIGINAL README for Tale (public archive):




----------------------



[![saythanks](https://img.shields.io/badge/say-thanks-ff69b4.svg)](https://saythanks.io/to/irmen)
[![Build Status](https://travis-ci.org/irmen/Tale.svg?branch=master)](https://travis-ci.org/irmen/Tale)
[![Latest Version](https://img.shields.io/pypi/v/tale.svg)](https://pypi.python.org/pypi/tale/)

![Tale logo](docs/source/_static/tale-large.png)

'Tale' - mud, mudlib & interactive fiction framework [frozen]
=============================================================

This software is copyright (c) by Irmen de Jong (irmen@razorvine.net).

This software is released under the GNU LGPL v3 software license.
This license, including disclaimer, is available in the 'LICENSE.txt' file.



Tale requires Python 3.5 or newer.
(If you have an older version of Python, stick to Tale 2.8 or older, which still supports Python 2.7 as well)

Required third party libraries:
- ``appdirs`` (to load and save games and config data in the correct folder).
- ``colorama`` (for stylized console output)
- ``serpent`` (to be able to create save game data from the game world)
- ``smartypants`` (for nicely quoted string output)
 
Optional third party library:
- ``prompt_toolkit``  (provides a nicer console text interface experience)

Read the documentation for more details on how to get started, see http://tale.readthedocs.io/

EXAMPLE STORIES
---------------

There is a trivial example built into tale, you can start it when you have the library installed
by simply typing:  ``python -m tale.demo.story``
 
On github and in the source distribution there are several much larger [example stories](stories/) and MUD examples.
* 'circle' - MUD that interprets CircleMud's data files and builds the world from those
* 'demo' - a random collection of stuff including a shop with some people
* 'zed_is_me' - a small single player (interactive fiction) survival adventure
