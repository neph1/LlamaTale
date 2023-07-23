
from tale.llm_ext import LivingNpc

class Patron(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, appearance: str, personality: str):
        super(Patron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, appearance=appearance, personality=personality, occupation='Student')
        
    def init(self) -> None:
        self.aliases = {"Patron"}

norhardt = Patron("Norhardt", "m", age=56, appearance="A grizzled old man, with parchment-like skin and sunken eyes. He\'s wearing ragged clothing and big leather boots. He\'s a formidable presence, commanding yet somber, clutching what looks like an old map", personality="An experienced explorer who is obsessed with finding the mythological Yeti which supposedly haunts these mountains. He won\'t stop talking about it.", descr="", short_descr="An old grizzled man sitting by the bar.")
norhardt.aliases = {"norhardt", "old man", "grizzled man"}

elid_gald = Patron("Elid Gald", "m", age=51, appearance="A gentleman who's aged with grace. He has a slender appearance with regal facial features, and dark hair, but his (one) eye has a dangerous squint. The other is covered by a patch.", personality="Old Gold is a smooth-talking pick-pocket and charlatan. Although claiming to be retired, he never passes on an opportunity to relieve strangers of their valuables.", short_descr="A slender gentleman with a patch over one of his eyes, leaning against the wall.")
elid_gald.aliases = {"elid", "one eyed man", "gentleman"}

shanda = Patron("Shanda Heard", "f", age=31, appearance="A fierce looking woman, with a face like chiseled from granite and a red bandana around her wild hair. She keeps an unblinking gaze on her surroundings.", personality="She's a heavy drinker and boaster, and for a free drink she will spill tales of her conquests and battles and long lost love. She's feared by many but respected by all for her prowess in battle.", short_descr="A fierce looking woman sitting by a table, whose eyes seem to follow you.")
shanda.aliases = {"shanda", "fierce woman", "woman by table"}

count_karta = Patron("Count of Karta", "m", age=43, appearance="A hood shadows his facial features, but a prominent jaw juts out. His mouth seems to be working constantly, as if muttering about something.", personality="Having fled from an attempt on his life, and being discredited, he has come here to plan his revenge. He seems to have gold and is looking for able bodies to help him.", short_descr="A mysterious man by the fire.")
count_karta.aliases = {"count", "karta", "mysterious man"}

urta = Patron("Urta", "f", age=44, appearance="A gruff, curvy woman with a long brown coat and bushy hair that reaches her waist. When not serving, she keeps polishing jugs with a dirty rag.", personality="She's the owner of the tavern, and of few words. But the words she speak are kind. She knows a little about all the patrons in her establishment.", short_descr="A curvy woman with long brown coat standing behind the bar.")
urta.aliases = {"bartender", "inn keeper", "curvy woman"}
