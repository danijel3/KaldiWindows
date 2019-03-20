#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import argparse
import subprocess
from pathlib import Path
from shutil import copy

'''
NOTE:
Deliberately omitted following files (needed only for training):
    - lang/topo
    - lang/sets*
    - lang/roots*
    - lang/extra_questions*
Assumes these programs are in path:
    - phonetisaurus-g2pfst
    - fstcompile
    - fstarcsort
'''

# Polish SAMPA only
nonsilence_phones = sorted(['I', 'S', 'Z', 'a', 'b', 'd', 'dZ', 'dz', 'dzi', 'e', 'en', 'f', 'g', 'i', 'j', 'k', 'l',
                            'm', 'n', 'ni', 'o', 'on', 'p', 'r', 's', 'si', 't', 'tS', 'ts', 'tsi', 'u', 'v', 'w', 'x',
                            'z', 'zi'])
silence_phones = sorted(['sil', 'spn'])
optional_silence = 'sil'

parser = argparse.ArgumentParser()
parser.add_argument('text')
parser.add_argument('temp_dir')
parser.add_argument('lang_dir')
parser.add_argument('--oov-word', default='<unk>')
parser.add_argument('--g2p-model', default='data/g2p/model.fst')
parser.add_argument('--g2p-lexicon', default='data/g2p/lexicon.txt')
parser.add_argument('--make-fst-bin', default='utils/make_lexicon_fst.py')

args = parser.parse_args()

text_path = Path(args.text)
g2p_path = Path(args.g2p_model)
g2p_lex_path = Path(args.g2p_lexicon)
oov = args.oov_word

lang_dir = Path(args.lang_dir)
temp_dir = Path(args.temp_dir)
phones_dir = lang_dir / 'phones'

lang_dir.mkdir(exist_ok=True)
temp_dir.mkdir(exist_ok=True)
phones_dir.mkdir(exist_ok=True)

transcription = []
wordlist = set()
with open(str(text_path), encoding='utf-8') as f:
    for l in f:
        for w in l.strip().split():
            wordlist.add(w)
            transcription.append(w)
wordlist = sorted(wordlist)

pre_lexicon = {}
with open(str(g2p_lex_path), encoding='utf-8') as f:
    for l in f:
        tok = l.strip().split()
        if tok[0] not in pre_lexicon:
            pre_lexicon[tok[0]] = []
        pre_lexicon[tok[0]].append(tok[1:])

with open(str(temp_dir / 'wordlist'), 'w', encoding='utf-8') as f:
    for w in wordlist:
        if w not in pre_lexicon:
            f.write(f'{w}\n')

with open(str(temp_dir / 'lexicon.raw'), 'w', encoding='utf-8') as f:
    subprocess.run(['phonetisaurus-g2pfst', '--pmass=0.8', '--nbest=10', f'--model={g2p_path}',
                    f'--wordlist={temp_dir / "wordlist"}'], stdout=f, stderr=subprocess.DEVNULL, check=True)

post_lexicon = {}
with open(str(temp_dir / 'lexicon.raw'), encoding='utf-8') as f:
    for l in f:
        tok = l.strip().split()
        if tok[0] not in pre_lexicon:
            post_lexicon[tok[0]] = []
        post_lexicon[tok[0]].append(tok[2:])

lexicon = []
lexicon.append((oov, ['spn']))
for w in wordlist:
    if w in pre_lexicon:
        t = pre_lexicon[w]
    else:
        w = post_lexicon[w]
    for tr in t:
        lexicon.append((w, tr))

for w, trans in lexicon:
    for ph in trans:
        assert ph in nonsilence_phones or ph in silence_phones, f'ERROR: {ph} is not a proper phoneme!'

# add _B_E_S_I
for w, trans in lexicon:
    if len(trans) == 1:
        trans[0] += '_S'
    else:
        trans[0] += '_B'
        if len(trans) > 2:
            for i in range(1, len(trans) - 1):
                trans[i] += '_I'
        trans[-1] += '_E'

with open(str(temp_dir / 'lexiconp.txt'), 'w', encoding='utf-8') as f:
    for w, trans in lexicon:
        f.write(f'{w}\t1.0\t{" ".join(trans)}\n')

# add_disambig

first_sym = 1  # 0 is reserved for wdisambig
max_disambig = first_sym - 1
reserved_empty = set()
last_sym = {}

count = {}  # number of identical transcripstions
for w, trans in lexicon:
    x = ' '.join(trans)
    if x not in count:
        count[x] = 1
    else:
        count[x] += 1

prefix = set()  # set of all possible prefixes (does not include full transcriptions)
for w, trans in lexicon:
    t = trans.copy()
    while len(t) > 0:
        t.pop()
        prefix.add(' '.join(t))

for w, trans in lexicon:
    x = ' '.join(trans)
    if x not in prefix and count[x] == 1:
        pass
    else:
        if len(x) == 0:
            max_disambig += 1
            reserved_empty.add(max_disambig)
            trans.append(f'#{max_disambig}')
        else:
            if x not in last_sym:
                curr_sym = first_sym
            else:
                curr_sym = last_sym[x] + 1
            while curr_sym in reserved_empty:
                curr_sym += 1
            if curr_sym > max_disambig:
                max_disambig = curr_sym
            last_sym[x] = curr_sym
            trans.append(f'#{curr_sym}')

max_disambig += 1
sil_disambig = max_disambig

with open(str(temp_dir / 'lexiconp_disambig.txt'), 'w', encoding='utf-8') as f:
    for w, trans in lexicon:
        f.write(f'{w}\t1.0\t{" ".join(trans)}\n')

with open(str(lang_dir / 'oov.txt'), 'w', encoding='utf-8') as f:
    f.write(f'{oov}\n')

counter = 0
phone_map = {}
phone_map['<eps>'] = counter
counter += 1
for ph in silence_phones:
    phone_map[ph] = counter
    counter += 1
    phone_map[ph + '_B'] = counter
    counter += 1
    phone_map[ph + '_E'] = counter
    counter += 1
    phone_map[ph + '_S'] = counter
    counter += 1
    phone_map[ph + '_I'] = counter
    counter += 1
for ph in nonsilence_phones:
    phone_map[ph + '_B'] = counter
    counter += 1
    phone_map[ph + '_E'] = counter
    counter += 1
    phone_map[ph + '_S'] = counter
    counter += 1
    phone_map[ph + '_I'] = counter
    counter += 1
for i in range(max_disambig + 1):
    phone_map[f'#{i}'] = counter
    counter += 1

with open(str(lang_dir / 'phones.txt'), 'w', encoding='utf-8') as f:
    for p, i in phone_map.items():
        f.write(f'{p} {i}\n')

counter = 0
words_map = {}
words_map['<eps>'] = counter
counter += 1
wordlist = set()
for w, t in lexicon:
    wordlist.add(w)
for w in sorted(wordlist):
    words_map[w] = counter
    counter += 1
words_map['#0'] = counter
counter += 1
words_map['<s>'] = counter
counter += 1
words_map['</s>'] = counter

with open(str(lang_dir / 'words.txt'), 'w', encoding='utf-8') as f:
    for w, i in words_map.items():
        f.write(f'{w} {i}\n')

with open(str(phones_dir / 'align_lexicon.txt'), 'w', encoding='utf-8') as f:
    for w, trans in lexicon:
        f.write(f'{w} {w} {" ".join(trans)}\n')
    f.write(f'<eps> <eps> {optional_silence}')

with open(str(phones_dir / 'silence.txt'), 'w', encoding='utf-8') as f:
    for ph in silence_phones:
        f.write(f'{ph}\n')
        f.write(f'{ph}_B\n')
        f.write(f'{ph}_E\n')
        f.write(f'{ph}_S\n')
        f.write(f'{ph}_I\n')

with open(str(phones_dir / 'nonsilence.txt'), 'w', encoding='utf-8') as f:
    for ph in nonsilence_phones:
        f.write(f'{ph}_B\n')
        f.write(f'{ph}_E\n')
        f.write(f'{ph}_S\n')
        f.write(f'{ph}_I\n')

with open(str(phones_dir / 'optional_silence.txt'), 'w', encoding='utf-8') as f:
    f.write(f'{optional_silence}\n')

copy(str(phones_dir / 'silence.txt'), str(phones_dir / 'context_indep.txt'))

with open(str(phones_dir / 'disambig.txt'), 'w', encoding='utf-8') as f:
    for i in range(max_disambig + 1):
        f.write(f'#{i}\n')

with open(str(phones_dir / 'wdisambig.txt'), 'w', encoding='utf-8') as f:
    f.write('#0\n')

with open(str(phones_dir / 'word_boundary.txt'), 'w', encoding='utf-8') as f:
    for set in ['silence.txt', 'nonsilence.txt']:
        with open(str(phones_dir / set),encoding='utf-8') as g:
            for l in g:
                l = l.strip()
                f.write(l)
                if l.endswith('_B'):
                    f.write(' begin\n')
                elif l.endswith('_E'):
                    f.write(' end\n')
                elif l.endswith('_S'):
                    f.write(' singleton\n')
                elif l.endswith('_I'):
                    f.write(' internal\n')
                else:
                    f.write(' nonword\n')


def range2fields(range_str, length):
    if len(range_str) == 0:
        return []
    if ',' in range_str:
        a = []
        for i in range_str.split(','):
            a.append(int(i.strip()))
        return a
    if '-' in range_str:
        if range_str[0] == '-':
            start = 0
        else:
            p = range_str.index('-')
            start = int(range_str[:p].strip())
        if range_str[1] == '-':
            end = length
        else:
            p = range_str.index('-')
            end = int(range_str[p + 1:].strip())
        return range(start, end)
    return [int(range_str.strip())]


def txt2int(txt, int, p_fields, w_fields):
    with open(str(txt), encoding='utf-8') as f:
        with open(str(int), 'w', encoding='utf-8') as g:
            for l in f:
                tok = l.strip().split()
                for f in range2fields(p_fields, len(tok)):
                    tok[f] = str(phone_map[tok[f]])
                for f in range2fields(w_fields, len(tok)):
                    tok[f] = str(words_map[tok[f]])
                g.write(' '.join(tok))
                g.write('\n')


txt2int(lang_dir / 'oov.txt', lang_dir / 'oov.int', '', '0')
txt2int(phones_dir / 'align_lexicon.txt', phones_dir / 'align_lexicon.int', '2-', '0,1')
txt2int(phones_dir / 'context_indep.txt', phones_dir / 'context_indep.int', '0', '')
txt2int(phones_dir / 'disambig.txt', phones_dir / 'disambig.int', '0', '')
txt2int(phones_dir / 'nonsilence.txt', phones_dir / 'nonsilence.int', '0', '')
txt2int(phones_dir / 'optional_silence.txt', phones_dir / 'optional_silence.int', '0', '')
txt2int(phones_dir / 'silence.txt', phones_dir / 'silence.int', '0', '')
txt2int(phones_dir / 'word_boundary.txt', phones_dir / 'word_boundary.int', '0', '')
txt2int(phones_dir / 'wdisambig.txt', phones_dir / 'wdisambig_phones.int', '0', '')
txt2int(phones_dir / 'wdisambig.txt', phones_dir / 'wdisambig_words.int', '', '0')

with open(str(temp_dir / 'trans.int'), 'w', encoding='utf-8') as f:
    f.write('input')
    for w in transcription:
        f.write(f' {words_map[w]}')
    f.write('\n')


def int2csl(int, csl):
    with open(str(int), encoding='utf-8') as f:
        with open(str(csl), 'w', encoding='utf-8') as g:
            a = []
            for l in f:
                a.append(l.strip())
            g.write(':'.join(a) + '\n')


int2csl(phones_dir / 'context_indep.int', phones_dir / 'context_indep.csl')
int2csl(phones_dir / 'disambig.int', phones_dir / 'disambig.csl')
int2csl(phones_dir / 'nonsilence.int', phones_dir / 'nonsilence.csl')
int2csl(phones_dir / 'optional_silence.int', phones_dir / 'optional_silence.csl')
int2csl(phones_dir / 'silence.int', phones_dir / 'silence.csl')

with open(str(temp_dir / 'lexicon_fst.txt'), 'w',encoding='utf-8') as f:
    subprocess.run([args.make_fst_bin, f'--sil-phone={optional_silence}', '--sil-prob=0.5',
                    f'{temp_dir / "lexiconp.txt"}'], stdout=f, stderr=subprocess.DEVNULL, check=True)

subprocess.run(['fstcompile', f'--isymbols={lang_dir / "phones.txt"}', f'--osymbols={lang_dir / "words.txt"}',
                '--keep_isymbols=false', '--keep_osymbols=false',
                str(temp_dir / 'lexicon_fst.txt'), str(temp_dir / 'lexicon_unsorted.fst')],
               stderr=subprocess.DEVNULL, check=True)

subprocess.run(['fstarcsort', '--sort_type=olabel',
                str(temp_dir / 'lexicon_unsorted.fst'), str(lang_dir / 'L.fst')],
               stderr=subprocess.DEVNULL, check=True)

with open(str(temp_dir / 'lexicon_disambig_fst.txt',encoding='utf-8'), 'w') as f:
    subprocess.run([args.make_fst_bin, f'--sil-phone={optional_silence}', '--sil-prob=0.5',
                    f'--sil-disambig=#{sil_disambig}', f'{temp_dir / "lexiconp_disambig.txt"}'],
                   stdout=f, stderr=subprocess.DEVNULL, check=True)

subprocess.run(['fstcompile', f'--isymbols={lang_dir / "phones.txt"}', f'--osymbols={lang_dir / "words.txt"}',
                '--keep_isymbols=false', '--keep_osymbols=false',
                str(temp_dir / 'lexicon_disambig_fst.txt'), str(temp_dir / 'lexicon_disambig_unsorted.fst')],
               stderr=subprocess.DEVNULL, check=True)

subprocess.run(['fstarcsort', '--sort_type=olabel',
                str(temp_dir / 'lexicon_disambig_unsorted.fst'), str(lang_dir / 'L_disambig.fst')],
               stderr=subprocess.DEVNULL, check=True)
