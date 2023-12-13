
<p align="center">
  <img src="https://github.com/neph1/LlamaTale/assets/7988802/35f5924c-77bb-4686-9127-07a3251f6873?raw=true" alt="A prancing Llama"/>
</p>
<p align="center"> Welcome to LlamaTale! </p>

What is LlamaTale?

It is a continuation of the archived IF/MUD framework Tale.

It uses an LLM backend to describe locations and npcs vivid way.

It generates dialogue for NPC's based on the story context and their character.

Check the wiki on how to get started : https://github.com/neph1/LlamaTale/wiki 

Or <a href="https://discord.gg/SmUNnPZXYd">join the discord server</a> if you have any questions.

![prancingllama3](https://github.com/neph1/LlamaTale/assets/7988802/07e382b9-2ae1-4230-82c8-3bcfb77556e2)


More features (See https://github.com/neph1/LlamaTale/releases for a more up to date list):
* Run the <a href="https://github.com/neph1/LlamaTale/wiki/The-Land-of-Anything-%E2%80%90-Prompt-your-own-story">'Anything' story</a> to get a completely customized world. Answer a few questions on what you'd like and the LLM will generate the world, background, world, common items and creatures.
* Npcs can have <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.18.0">pre-defined avatars</a>, which are used when talking to them.
* Npcs have 'idle' actions and reactions, brought to life by the LLM. This sometimes leads to <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.11.0">drama</a>.
* Use Stable Diffusion to generate avatars for npcs you meet.
* Use <a href="https://github.com/neph1/LlamaTale/wiki/Be-a-Game-Master">"Game Master"</a> commands to affect the world and characters.
* Combat results are rolled by the MUD, but the LLM tries to describe them in a more fluid way.
* Characters have a memories of past events and conversations, as well as a flexible 'sentiment' towards other characters.
* You can mix predefined locations with dynamically generated ones. Ie, create a base and let the LLM do the rest.
* <a href="https://github.com/neph1/LlamaTale/releases/tag/v0.17.0">Quests</a>. See new places and meet new people with the (simple) automated quest system.
* Support for KoboldCpp and OpenAI API based backends.


Old Example of talking to Elid:
 
  You say: elid: ’what are you doing here?’.

>   Elid Gald says: “Elid Gald chuckles mischievously at Arto’s question
  and smirks, adjusting his hat before responding, “Why, I’m just
  enjoying a stroll through the market, my dear sir.  And what about
  yourself?  What brings you to these parts?”  His voice is smooth and
  alluring with an undercurrent of danger hidden beneath it.”

  You say: elid: ’i’m looking for some goods to buy, my purse is laden
  with gold’.

>   Elid Gald says: “Elid Gald nods approvingly at Arto’s mention of
  wealth and grins wickedly, leaning in closer to whisper, “Well then,
  perhaps I can help you find something truly unique and valuable.
  Perhaps some items that are not available on the open market, eh?  You
  see, I have connections with certain…merchants who might be willing
  to part with their finest wares for someone like you.”  He pauses
  meaningfully, allowing the implication to linger in the air between
  them as his hand slips casually into his pocket.As he speaks, one
  could almost hear the clinking of coins in his pocket - but whether
  it’s real or just a clever illusion is anyone’s guess.  “You know,” he
  says softly, “I’ve always been known for my eye for rare and exquisite
  goods.  Why not let me help you acquire something truly special?
  After all, I’m sure you don’t want to be caught with common trinkets.”
  His voice is silky smooth and seductive as he leans even closer to
  Arto, a glint of mischief in his remaining eye.”Wouldn’t you
  rather have something that sets you apart from others?  Something that
  screams ’wealthy aristocrat’?””

You say: elid: ’maybe you’re right.. do you charge a fee for your
  services?’.

>   Elid Gald says: “Elid Gald chuckles softly and takes a step back,
  giving Arto an appraising look.  “I always charge a fee, young man,”
  he says with a smirk, “And my fee is quite substantial.  But I believe
  that the items I can help you acquire will be more than worth it.”
  His voice is still silky smooth and seductive, his mischievous gaze
  never leaving Arto’s face.\n”However,” He continues, “If you’re
  willing to make a deal with me… let’s say, a mutually beneficial
  agreement… then we could discuss a different kind of payment.”  He
  winks at Arto, his remaining eye gleaming with curiosity.”What do
  you think?  Are you willing to take a risk for something truly
  unique?””

