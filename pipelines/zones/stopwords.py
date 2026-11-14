"""A small stop list for zone words: the languages the corpus holds most, plus platform noise.

Class-based TF-IDF already lowers words every zone uses. It cannot lower the function words of
a language that fills one zone only, hence this list.
"""

_ENGLISH = """
the and for that this with you your are was were not but have has had his her she him they them
their there here what when where who whom why how all any can could should would will just from
into about over out off our ours its been being than then too very more most some such only
own same also get got one two new now like did does doing because while which these those after
don didn doesn isn aren wasn weren won wouldn couldn shouldn haven hasn hadn ain
before again further once both each few other until against between through during above below
may might must shall say says said see know think going want need make made back still even
much many well really ever never every today
"""

_RUSSIAN = """
это как так что для его она они оно мы вы ты при про под над без или уже еще ещё тоже также
если когда чтобы потому только очень может быть был была было были есть нет все всё всех всем
этот эта эти того тот том там тут где кто чем чего который которая которые свой своя свои
наш ваш мне меня тебя тебе нас вас них ним него нее неё ему ей им себя будет будут после
перед через между более менее даже лишь вот ведь либо ничего сейчас теперь раз два
"""

_GERMAN = """
der die das und ist nicht mit ein eine einen einem einer den dem des für auf von zu zum zur
sich auch wie wir ihr sie ich aber oder wenn dass daß als noch nur schon man bei aus nach
über unter vor hat haben wird werden war sind kann mehr sehr was wer wo
"""

_PLATFORM = "http https www com co rt via amp"

STOP_WORDS = frozenset(" ".join((_ENGLISH, _RUSSIAN, _GERMAN, _PLATFORM)).split())
