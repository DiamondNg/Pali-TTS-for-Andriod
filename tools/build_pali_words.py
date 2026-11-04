"""Builds pali_words.py: the most frequent Pāli word forms of the Suttas and Vinaya
(SuttaCentral bilara-data, Mahāsaṅgīti root text), for language detection.

Usage: python3 tools/build_pali_words.py BILARA_DIR [--count 50000] [--english 3000] [--hold-out an10]
  BILARA_DIR: a checkout of github.com/suttacentral/bilara-data (branch "published"),
  sparse checkout of root/pli/ms and translation/en is enough.
Words of 1–2 letters (ca, na, so, te, me, no …) are left out on purpose: they are
also words of English, Spanish, Malay… Plain-letter forms (bhikkhave → same; dhammaṁ →
dhammam) are made by the app when it loads the list, except those that are English
words (NOT_PLAIN: "same", "pace" …). ENGLISH: common English words that are never Pāli.
"""
import argparse
import collections
import glob
import json
import os
import re
import unicodedata

WORD = re.compile(r"[a-zāīūṃṁṅñṭḍṇḷ]+")
FOLD = str.maketrans("āīūṃṁṅñṭḍṇḷ", "aiummnntdnl")


def segments(pattern, hold_out):
    for f in sorted(glob.glob(pattern, recursive=True)):
        if hold_out and re.search(r"[/_]%s[._/]" % re.escape(hold_out), f.replace(os.sep, "/")):
            continue
        for v in json.load(open(f, encoding="utf-8")).values():
            yield unicodedata.normalize("NFC", v).lower().replace("ṃ", "ṁ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bilara")
    ap.add_argument("--count", type=int, default=50000)
    ap.add_argument("--hold-out", default="", help="collection left out (for testing)")
    ap.add_argument("--english", type=int, default=3000)
    ap.add_argument("--out", default="pali_words.py")
    a = ap.parse_args()
    root = os.path.join(a.bilara, "root", "pli", "ms")
    freq = collections.Counter()
    for part in ("sutta", "vinaya"):
        for seg in segments(os.path.join(root, part, "**", "*.json"), a.hold_out):
            freq.update(w for w in WORD.findall(seg) if len(w) > 2)
    english = collections.Counter()
    for seg in segments(os.path.join(a.bilara, "translation", "en", "**", "*.json"), ""):
        english.update(re.findall(r"[a-z]+", seg))
    words = sorted(w for w, _ in freq.most_common(a.count))
    pali_all = set(freq)
    plain_pali = {w.translate(FOLD) for w in pali_all}
    # Plain spellings that are English words: not taken as Pāli without diacritics
    not_plain = sorted({w.translate(FOLD) for w in words} & set(english) - set(words))
    # Common English words that are never Pāli (any spelling): evidence for English
    eng = [w for w, _ in english.most_common()
           if len(w) > 2 and w not in pali_all and w not in plain_pali][:a.english]
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write('"""Word lists for language detection. Made by tools/build_pali_words.py from\n'
                'SuttaCentral bilara-data (Mahāsaṅgīti root text; Sujato/Brahmali translations).\n'
                'Do not edit by hand.\n\n'
                'WORDS: the %d most frequent Pāli word forms (3+ letters) of the Suttas and Vinaya.\n'
                'NOT_PLAIN: their spellings without diacritics that are English words ("same").\n'
                'ENGLISH: the %d most frequent words of the English translations that never occur\n'
                'in Pāli."""\n' % (len(words), len(eng)))
        for name, items in (("WORDS", words), ("NOT_PLAIN", not_plain), ("ENGLISH", sorted(eng))):
            f.write('\n%s = """\n%s\n"""\n' % (name, "\n".join(items)))
    print("%d Pāli words, %d not-plain, %d English; %d bytes -> %s"
          % (len(words), len(not_plain), len(eng), os.path.getsize(a.out), a.out))


if __name__ == "__main__":
    main()
