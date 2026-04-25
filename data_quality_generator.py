"""
data_quality_generator.py

Generates word variations that represent common data quality issues.
Each function implements one variation sub-type from the word variation taxonomy.
All functions are pure Python and use only the standard library.
"""

import math
import random
import string
import sys
import json

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

KEYBOARD_ADJACENCY = {
    'q': 'wa',    'w': 'qeasd', 'e': 'wrsdf', 'r': 'etdfg', 't': 'ryfgh',
    'y': 'tughj', 'u': 'yihjk', 'i': 'uojkl', 'o': 'ipkl',  'p': 'ol',
    'a': 'qwsz',  's': 'awedxz','d': 'serfcx','f': 'drtgvc', 'g': 'ftyhbv',
    'h': 'gyujnb','j': 'huikmn','k': 'jiolm', 'l': 'kop',
    'z': 'asx',   'x': 'zsdc',  'c': 'xdfv',  'v': 'cfgb',   'b': 'vghn',
    'n': 'bhjm',  'm': 'njk',
}

HOMOPHONES = {
    'to':     ['too', 'two'],
    'there':  ['their', "they're"],
    'here':   ['hear'],
    'right':  ['write'],
    'know':   ['no'],
    'new':    ['knew'],
    'see':    ['sea'],
    'be':     ['bee'],
    'by':     ['buy', 'bye'],
    'for':    ['four', 'fore'],
    'one':    ['won'],
    'ate':    ['eight'],
    'hour':   ['our'],
    'flower': ['flour'],
    'mail':   ['male'],
    'meet':   ['meat'],
    'piece':  ['peace'],
    'plain':  ['plane'],
    'rain':   ['reign', 'rein'],
    'sole':   ['soul'],
    'sun':    ['son'],
    'tail':   ['tale'],
    'way':    ['weigh'],
    'week':   ['weak'],
    'wear':   ['where'],
}

REGIONAL_SPELLINGS = {
    'color':     'colour',
    'center':    'centre',
    'analyze':   'analyse',
    'defense':   'defence',
    'gray':      'grey',
    'humor':     'humour',
    'license':   'licence',
    'organize':  'organise',
    'recognize': 'recognise',
    'flavor':    'flavour',
    'honor':     'honour',
    'labor':     'labour',
    'neighbor':  'neighbour',
    'favor':     'favour',
    'behavior':  'behaviour',
    'program':   'programme',
    'dialog':    'dialogue',
    'catalog':   'catalogue',
    'realize':   'realise',
    'apologize': 'apologise',
}

INFORMAL_FORMS = {
    'going':      'goin',
    'nothing':    'nothin',
    'something':  'somethin',
    'everything': 'everythin',
    'talking':    'talkin',
    'walking':    'walkin',
    'running':    'runnin',
    'because':    'cuz',
    'you':        'u',
    'your':       'ur',
    'are':        'r',
    'before':     'b4',
    'great':      'gr8',
    'later':      'l8r',
    'people':     'ppl',
    'please':     'plz',
    'thanks':     'thx',
    'tonight':    '2nite',
    'tomorrow':   '2moro',
    'message':    'msg',
}

ABBREVIATIONS = {
    'street':        'st',
    'avenue':        'ave',
    'boulevard':     'blvd',
    'drive':         'dr',
    'road':          'rd',
    'mister':        'mr',
    'doctor':        'dr',
    'professor':     'prof',
    'january':       'jan',
    'february':      'feb',
    'march':         'mar',
    'april':         'apr',
    'august':        'aug',
    'september':     'sep',
    'october':       'oct',
    'november':      'nov',
    'december':      'dec',
    'department':    'dept',
    'company':       'co',
    'incorporated':  'inc',
    'limited':       'ltd',
    'approximately': 'approx',
    'maximum':       'max',
    'minimum':       'min',
    'number':        'no',
    'telephone':     'tel',
    'versus':        'vs',
}

SHORTENED_FORMS = {
    'alexander':   'alex',
    'william':     'bill',
    'robert':      'rob',
    'elizabeth':   'liz',
    'jennifer':    'jen',
    'michael':     'mike',
    'christopher': 'chris',
    'katherine':   'kate',
    'matthew':     'matt',
    'nicholas':    'nick',
    'jonathan':    'jon',
    'benjamin':    'ben',
    'stephanie':   'steph',
    'thomas':      'tom',
    'patricia':    'pat',
    'timothy':     'tim',
    'barbara':     'barb',
    'richard':     'rick',
    'nathaniel':   'nate',
    'jessica':     'jess',
}

PHONEME_MAP = {
    'tch': 'ch',
    'dge': 'j',
    'ph':  'f',
    'ck':  'k',
    'ce':  'se',
    'ci':  'si',
    'gh':  'g',
    'kn':  'n',
    'wr':  'r',
    'mb':  'm',
    'qu':  'kw',
    'x':   'ks',
}

SILENT_LETTERS = {
    'knight':     'night',
    'knife':      'nife',
    'know':       'no',
    'kneel':      'neel',
    'wrap':       'rap',
    'write':      'rite',
    'wrong':      'rong',
    'wrist':      'rist',
    'gnome':      'nome',
    'gnat':       'nat',
    'thumb':      'thum',
    'lamb':       'lam',
    'bomb':       'bom',
    'comb':       'com',
    'debt':       'det',
    'doubt':      'dout',
    'hour':       'our',
    'honest':     'onest',
    'psychology': 'sychology',
    'pneumonia':  'neumonia',
    'castle':     'casle',
    'whistle':    'wisle',
}

VOWEL_SHIFT_MAP = {
    'ou': 'o',
    'er': 'or',
    'ir': 'ur',
    'or': 'ar',
    'ea': 'ee',
    'ai': 'ay',
    'oa': 'o',
    'oo': 'u',
    'ie': 'ee',
    'ei': 'ay',
    'au': 'aw',
    'ew': 'oo',
}

PREFIX_LIST = ['un', 'pre', 'mis', 're', 'in', 'dis', 'im', 'il', 'non', 'over', 'sub', 'super']

SUFFIX_LIST = ['ing', 'tion', 'ment', 'ness', 'less', 'ful', 'able', 'ible',
               'ity', 'ism', 'ist', 'er', 'est', 'ly', 'ed', 's']

ACCENT_MAP = {
    'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú',
    'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú',
    'n': 'ñ', 'c': 'ç',
}

LOOKALIKE_MAP = {
    'o': '0', 'l': '1', 'i': '!', 's': '5', 'e': '3',
    'a': '@', 'b': '6', 'g': '9', 't': '7', 'z': '2',
}

COMPOUND_WORDS = {
    'notebook':   'note book',
    'football':   'foot ball',
    'bedroom':    'bed room',
    'sunshine':   'sun shine',
    'keyboard':   'key board',
    'airport':    'air port',
    'birthday':   'birth day',
    'basketball': 'basket ball',
    'rainbow':    'rain bow',
    'sunflower':  'sun flower',
    'doorbell':   'door bell',
    'moonlight':  'moon light',
    'bookshelf':  'book shelf',
    'firework':   'fire work',
    'highway':    'high way',
    'downtown':   'down town',
    'baseball':   'base ball',
    'classroom':  'class room',
    'newspaper':  'news paper',
    'username':   'user name',
}

NUMBER_SUBSTITUTIONS = {
    'for':     '4',
    'to':      '2',
    'too':     '2',
    'ate':     '8',
    'be':      'b',
    'one':     '1',
    'won':     '1',
    'are':     'r',
    'you':     'u',
    'see':     'c',
    'why':     'y',
    'oh':      '0',
    'before':  'b4',
    'great':   'gr8',
    'later':   'l8r',
    'tonight': '2nite',
}

# ---------------------------------------------------------------------------
# Category 1 — Character-Level Variations
# ---------------------------------------------------------------------------

def char_insertion(dict: dict) -> dict:
    """Insert a random letter at a random position."""
    for word in dict:
        if not word:
            return word
        pos = random.randint(0, len(word))
        letter = random.choice(string.ascii_lowercase)
        dict[word].add(word[:pos] + letter + word[pos:])
        return dict


def char_deletion(dict: dict) -> dict:
    """Delete one random character."""
    for word in dict:
        if len(word) <= 1:
            return word
        pos = random.randint(0, len(word) - 1)
        dict[word].add(word[:pos] + word[pos + 1:])
        return dict


def char_substitution(dict: dict) -> dict:
    """Replace one random character with a different letter (preserving case)."""
    for word in dict:
        if not word:
            return word
        pos = random.randint(0, len(word) - 1)
        original = word[pos].lower()
        candidates = [c for c in string.ascii_lowercase if c != original]
        replacement = random.choice(candidates)
        if word[pos].isupper():
            replacement = replacement.upper()
        dict[word].add(word[:pos] + replacement + word[pos + 1:])
        return dict


def char_transposition(dict: dict) -> dict:
    """Swap two adjacent characters at a random position."""
    for word in dict:
        if len(word) < 2:
            return word
        pos = random.randint(0, len(word) - 2)
        chars = list(word)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        dict[word].add(''.join(chars))
        return dict


def char_repetition(dict: dict) -> dict:
    """Duplicate one random character."""
    for word in dict:
        if not word:
            return word
        pos = random.randint(0, len(word) - 1)
        dict[word].add(word[:pos + 1] + word[pos] + word[pos + 1:])
        return dict


def char_truncation(dict: dict) -> dict:
    """Remove trailing characters, keeping at least half the word."""
    for word in dict:
        if len(word) <= 2:
            return word
        min_len = max(1, len(word) // 2)
        new_len = random.randint(min_len, len(word) - 1)
        dict[word].add(word[:new_len])
        return dict


# ---------------------------------------------------------------------------
# Category 2 — Phonetic Variations
# ---------------------------------------------------------------------------

def phonetic_substitution(dict: dict) -> dict:
    """Apply phoneme map rules (e.g. ph->f, ck->k)."""
    for word in dict:
        result = word.lower()
        for pattern, replacement in sorted(PHONEME_MAP.items(), key=lambda x: -len(x[0])):
            if pattern in result:
                result = result.replace(pattern, replacement, 1)
                break
        dict[word].add(result)
        return dict


def phonetic_silent_letter_removal(dict: dict) -> dict:
    """Remove silent letters using the lookup table."""
    for word in dict:
        dict[word].add(SILENT_LETTERS.get(word.lower(), word))
        return dict


def phonetic_vowel_shift(dict: dict) -> dict:
    """Shift a vowel pattern or a single vowel to an alternative."""
    for word in dict:
        result = word.lower()
        for pattern, replacement in sorted(VOWEL_SHIFT_MAP.items(), key=lambda x: -len(x[0])):
            if pattern in result:
                dict[word].add(result.replace(pattern, replacement, 1))
                return dict
        vowel_positions = [i for i, c in enumerate(result) if c in 'aeiou']
        if not vowel_positions:
            return word
        pos = random.choice(vowel_positions)
        other_vowels = [v for v in 'aeiou' if v != result[pos]]
        chars = list(result)
        chars[pos] = random.choice(other_vowels)
        dict[word].add(''.join(chars))
        return dict


def phonetic_homophone(dict: dict) -> dict:
    """Return a homophone of the word if one exists."""
    for word in dict:
        options = HOMOPHONES.get(word.lower())
        if options:
            dict[word].add(random.choice(options))
        else:
            dict[word].add(word)
        return dict


# ---------------------------------------------------------------------------
# Category 3 — Orthographic Variations
# ---------------------------------------------------------------------------

def ortho_regional_spelling(dict: dict) -> dict:
    """Toggle between US and UK spelling."""
    for word in dict:
        key = word.lower()
        if key in REGIONAL_SPELLINGS:
            dict[word].add(REGIONAL_SPELLINGS[key])
        else:
            reverse = {v: k for k, v in REGIONAL_SPELLINGS.items()}
            if key in reverse:
                dict[word].add(reverse[key])
            else:
                dict[word].add(word)
        return dict


def ortho_informal(dict: dict) -> dict:
    """Return the informal/text-speak form of the word."""
    for word in dict:
        dict[word].add(INFORMAL_FORMS.get(word.lower(), word))
        return dict


def ortho_case_change(dict: dict) -> dict:
    """Randomly apply UPPER, lower, Title, or rAnDoM casing."""
    for word in dict:
        mode = random.choice(['upper', 'lower', 'title', 'random'])
        if mode == 'upper':
            dict[word].add(word.upper())
        elif mode == 'lower':
            dict[word].add(word.lower())
        elif mode == 'title':
            dict[word].add(word.title())
        else:
            dict[word].add(''.join(c.upper() if random.random() > 0.5 else c.lower() for c in word))
        return dict


def ortho_punctuation_removal(dict: dict) -> dict:
    """Strip apostrophes, hyphens, periods, underscores, commas, and exclamation marks."""
    for word in dict:
        dict[word].add(word.translate(str.maketrans('', '', ".'\\-_,!")))
        return dict


# ---------------------------------------------------------------------------
# Category 4 — Morphological Variations
# ---------------------------------------------------------------------------

def morph_inflection(dict: dict) -> dict:
    """Apply a random inflectional ending (-ing, -ed, -s, -er, -est)."""
    for word in dict:
        if not word:
            return word
        form = random.choice(['ing', 'ed', 's', 'er', 'est'])
        w = word.lower()
        vowels = set('aeiou')

        if form == 'ing':
            if len(w) > 2 and w[-1] == 'e':
                dict[word].add(w[:-1] + 'ing')
            elif len(w) >= 3 and w[-1] not in vowels and w[-2] in vowels and w[-3] not in vowels:
                dict[word].add(w + w[-1] + 'ing')
            else:
                dict[word].add(w + 'ing')
        elif form == 'ed':
            if w[-1] == 'e':
                dict[word].add(w + 'd')
            elif len(w) >= 3 and w[-1] not in vowels and w[-2] in vowels and w[-3] not in vowels:
                dict[word].add(w + w[-1] + 'ed')
            else:
                dict[word].add(w + 'ed')
        elif form == 's':
            if w[-1] in ('s', 'x', 'z') or w[-2:] in ('sh', 'ch'):
                dict[word].add(w + 'es')
            elif w[-1] == 'y' and len(w) >= 2 and w[-2] not in vowels:
                dict[word].add(w[:-1] + 'ies')
            else:
                dict[word].add(w + 's')
        else:
            if w[-1] == 'e':
                dict[word].add(w + form[1:])
            else:
                dict[word].add(w + form)
        return dict


def morph_derivation(dict: dict) -> dict:
    """Add a derivational suffix."""
    for word in dict:
        candidates = [s for s in SUFFIX_LIST if s not in ('ed', 's', 'est')]
        suffix = random.choice(candidates)
        w = word.lower()
        if w[-1] == 'e' and suffix[0] in 'aeiou':
            dict[word].add(w[:-1] + suffix)
        else:
            dict[word].add(w + suffix)
        return dict


def morph_stemming(dict: dict) -> dict:
    """Strip the longest known suffix (keeping at least 3 root characters)."""
    for word in dict:
        w = word.lower()
        for suffix in sorted(SUFFIX_LIST, key=len, reverse=True):
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                dict[word].add(w[:-len(suffix)])
                return dict
        dict[word].add(word)
        return dict


def morph_affix(dict: dict) -> dict:
    """Prepend a random prefix."""
    for word in dict:
        prefix = random.choice(PREFIX_LIST)
        dict[word].add(prefix + word.lower())
        return dict


# ---------------------------------------------------------------------------
# Category 5 — Abbreviation & Expansion
# ---------------------------------------------------------------------------

def abbrev_abbreviation(dict: dict) -> dict:
    """Return the standard abbreviation, or first 3 chars + period as fallback."""
    for word in dict:
        key = word.lower()
        if key in ABBREVIATIONS:
            dict[word].add(ABBREVIATIONS[key])
        elif len(word) > 3:
            dict[word].add(word[:3].lower() + '.')
        else:
            dict[word].add(word)
        return dict


def abbrev_acronym(dict: dict) -> dict:
    """Return initials for multi-word input, or full uppercase for single word."""
    for word in dict:
        if ' ' in word:
            dict[word].add(''.join(w[0].upper() for w in word.split() if w))
        else:
            dict[word].add(word.upper())
        return dict


def abbrev_shortened_form(dict: dict) -> dict:
    """Return a known shortened form, or the first half of the word."""
    for word in dict:
        key = word.lower()
        if key in SHORTENED_FORMS:
            dict[word].add(SHORTENED_FORMS[key])
        else:
            half = math.ceil(len(word) / 2)
            dict[word].add(word[:half])
        return dict


# ---------------------------------------------------------------------------
# Category 6 — Keyboard / Typo Variations
# ---------------------------------------------------------------------------

def typo_adjacent_key(dict: dict) -> dict:
    """Replace one character with an adjacent key on a QWERTY layout."""
    for word in dict:
        if not word:
            return word
        candidates = [i for i, c in enumerate(word) if c.lower() in KEYBOARD_ADJACENCY]
        if not candidates:
            return word
        pos = random.choice(candidates)
        c = word[pos].lower()
        adjacent = KEYBOARD_ADJACENCY[c]
        replacement = random.choice(adjacent)
        if word[pos].isupper():
            replacement = replacement.upper()
        dict[word].add(word[:pos] + replacement + word[pos + 1:])
        return dict


def typo_missed_keystroke(dict: dict) -> dict:
    """Simulate a missed keystroke by deleting one random character."""
    return char_deletion(dict)


def typo_double_key_press(dict: dict) -> dict:
    """Simulate a double key press by duplicating one random character."""
    return char_repetition(dict)


def typo_wrong_key_order(dict: dict) -> dict:
    """Simulate wrong key order by transposing two adjacent characters."""
    return char_transposition(dict)


# ---------------------------------------------------------------------------
# Category 7 — Token-Level Variations
# ---------------------------------------------------------------------------

def token_split(dict: dict) -> dict:
    """Split a compound word into two tokens."""
    for word in dict:
        key = word.lower()
        if key in COMPOUND_WORDS:
            dict[word].add(COMPOUND_WORDS[key])
        elif len(word) < 4:
            return word
        else:
            mid = random.randint(2, len(word) - 2)
            dict[word].add(word[:mid] + ' ' + word[mid:])
        return dict


def token_merge(dict: dict) -> dict:
    """Merge a multi-token string into a single token."""
    for word in dict:
        if ' ' in word:
            dict[word].add(word.replace(' ', ''))
        else:
            dict[word].add(word)
        return dict


def token_reorder(dict: dict) -> dict:
    """Shuffle the order of tokens in a multi-word string."""
    for word in dict:
        tokens = word.split()
        if len(tokens) < 2:
            return word
        random.shuffle(tokens)
        dict[word].add(' '.join(tokens))
        return dict


# ---------------------------------------------------------------------------
# Category 8 — Noise Injection
# ---------------------------------------------------------------------------

def noise_random(dict: dict) -> dict:
    """Replace one random character with a random digit."""
    for word in dict:
        if not word:
            return word
        pos = random.randint(0, len(word) - 1)
        digit = random.choice(string.digits)
        dict[word].add(word[:pos] + digit + word[pos + 1:])
        return dict


def noise_number_substitution(dict: dict) -> dict:
    """Substitute the whole word with its number/symbol equivalent if known."""
    for word in dict:
        dict[word].add(NUMBER_SUBSTITUTIONS.get(word.lower(), word))
        return dict


# ---------------------------------------------------------------------------
# Category 9 — Unicode / Encoding
# ---------------------------------------------------------------------------

def unicode_accent(dict: dict) -> dict:
    """Replace a random accented-capable character with its accented form."""
    for word in dict:
        candidates = [i for i, c in enumerate(word) if c in ACCENT_MAP]
        if not candidates:
            return word
        pos = random.choice(candidates)
        dict[word].add(word[:pos] + ACCENT_MAP[word[pos]] + word[pos + 1:])
        return dict


def unicode_lookalike(dict: dict) -> dict:
    """Replace a random character with a visually similar substitute."""
    for word in dict:
        candidates = [i for i, c in enumerate(word) if c.lower() in LOOKALIKE_MAP]
        if not candidates:
            return word
        pos = random.choice(candidates)
        replacement = LOOKALIKE_MAP[word[pos].lower()]
        dict[word].add(word[:pos] + replacement + word[pos + 1:])
        return dict


# ---------------------------------------------------------------------------
# Category 10 — N-gram Variations
# ---------------------------------------------------------------------------

def ngram_substrings(dict: dict, n: int = 3) -> dict:
    """Return non-overlapping substrings of length n."""
    for word in dict:
        if len(word) < n:
            dict[word].add(word)
            return dict
        fragments = [word[i:i + n] for i in range(0, len(word) - n + 1, n)]
        dict[word].update(fragments)
        return dict


def ngram_overlapping_fragments(dict: dict, n: int = 4) -> dict:
    """Return all overlapping fragments of length n (sliding by 1)."""
    for word in dict:
        if len(word) < n:
            dict[word].add(word)
            return dict
        fragments = [word[i:i + n] for i in range(len(word) - n + 1)]
        dict[word].update(fragments)
        return dict


# ---------------------------------------------------------------------------
# Category 11 — Hybrid Variations
# ---------------------------------------------------------------------------

_TRANSFORM_POOL = [
    char_insertion,
    char_deletion,
    char_substitution,
    char_transposition,
    char_repetition,
    phonetic_substitution,
    ortho_case_change,
    typo_adjacent_key,
    noise_random,
    unicode_lookalike,
    unicode_accent,
    morph_affix,
    morph_stemming,
]


def hybrid_combination(dict: dict, n_transforms: int = 2) -> dict:
    """Apply n_transforms randomly chosen variation functions sequentially."""
    for word in dict:
        transforms = random.sample(_TRANSFORM_POOL, min(n_transforms, len(_TRANSFORM_POOL)))
        current_word = word
        for transform in transforms:
            temp = {current_word: set()}
            transform(temp)
            if temp[current_word]:
                current_word = next(iter(temp[current_word]))
        dict[word].add(current_word)
        return dict


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def generate_all_variations(word: str) -> dict:
    """
    Generate all variation types for a given word.

    Initializes {word: set()} then passes the dict through every
    variation function. Returns the populated dict.
    """
    d = {word: set()}

    char_insertion(d);              char_deletion(d);           char_substitution(d)
    char_transposition(d);          char_repetition(d);         char_truncation(d)

    phonetic_substitution(d);       phonetic_silent_letter_removal(d)
    phonetic_vowel_shift(d);        phonetic_homophone(d)

    ortho_regional_spelling(d);     ortho_informal(d)
    ortho_case_change(d);           ortho_punctuation_removal(d)

    morph_inflection(d);            morph_derivation(d)
    morph_stemming(d);              morph_affix(d)

    abbrev_abbreviation(d);         abbrev_acronym(d);          abbrev_shortened_form(d)

    typo_adjacent_key(d);           typo_missed_keystroke(d)
    typo_double_key_press(d);       typo_wrong_key_order(d)

    token_split(d);                 token_merge(d);             token_reorder(d)

    noise_random(d);                noise_number_substitution(d)

    unicode_accent(d);              unicode_lookalike(d)

    ngram_substrings(d);            ngram_overlapping_fragments(d)

    hybrid_combination(d)

    return d


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    input_word = sys.argv[1] if len(sys.argv) > 1 else "frank"
    result = generate_all_variations(input_word)
    serialisable = {k: sorted(v) for k, v in result.items()}
    print(json.dumps(serialisable, ensure_ascii=False, indent=2))
