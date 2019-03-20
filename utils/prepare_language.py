#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path

# Polish SAMPA only
from utils.kaldi_programs import KaldiPrograms
from utils.log import log

nonsilence_phones = sorted(['I', 'S', 'Z', 'a', 'b', 'd', 'dZ', 'dz', 'dzi', 'e', 'en', 'f', 'g', 'i', 'j', 'k', 'l',
                            'm', 'n', 'ni', 'o', 'on', 'p', 'r', 's', 'si', 't', 'tS', 'ts', 'tsi', 'u', 'v', 'w', 'x',
                            'z', 'zi'])
silence_phones = sorted(['sil', 'spn'])
optional_silence = 'sil'


def prepare_language_file(text_path, output_dir, g2p_path, g2p_lex_path, oov, kaldi):
    log.info(f'Using {text_path} to prepare language files in {output_dir}.')

    transcription = {}
    wordlist = set()
    with open(str(text_path), encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            id = tok[0]
            transcription[id] = []
            for w in tok[1:]:
                wordlist.add(w)
                transcription[id].append(w)
    wordlist = sorted(wordlist)

    pre_lexicon = {}
    with open(str(g2p_lex_path), encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            if tok[0] not in pre_lexicon:
                pre_lexicon[tok[0]] = []
            pre_lexicon[tok[0]].append(tok[1:])

    with open(str(output_dir / 'wordlist'), 'w', encoding='utf-8') as f:
        for w in wordlist:
            if w not in pre_lexicon:
                f.write(f'{w}\n')

    kaldi.phonetisaurus_g2p(g2p_path, output_dir / 'wordlist', output_dir / 'lexicon.raw')

    post_lexicon = {}
    with open(str(output_dir / 'lexicon.raw'), encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            if tok[0] not in pre_lexicon:
                post_lexicon[tok[0]] = []
            post_lexicon[tok[0]].append(tok[2:])

    lexicon = []
    lexicon.append((oov, 1.0, ['spn']))
    for w in wordlist:
        if w in pre_lexicon:
            t = pre_lexicon[w]
        else:
            t = post_lexicon[w]
        for tr in t:
            lexicon.append((w, 1.0, tr))

    for w, p, trans in lexicon:
        for ph in trans:
            assert ph in nonsilence_phones or ph in silence_phones, f'ERROR: {ph} is not a proper phoneme!'

    # add _B_E_S_I
    for w, p, trans in lexicon:
        if len(trans) == 1:
            trans[0] += '_S'
        else:
            trans[0] += '_B'
            if len(trans) > 2:
                for i in range(1, len(trans) - 1):
                    trans[i] += '_I'
            trans[-1] += '_E'

    # add_disambig
    first_sym = 1  # 0 is reserved for wdisambig
    max_disambig = first_sym - 1
    reserved_empty = set()
    last_sym = {}

    count = {}  # number of identical transcripstions
    for w, p, trans in lexicon:
        x = ' '.join(trans)
        if x not in count:
            count[x] = 1
        else:
            count[x] += 1

    prefix = set()  # set of all possible prefixes (does not include full transcriptions)
    for w, p, trans in lexicon:
        t = trans.copy()
        while len(t) > 0:
            t.pop()
            prefix.add(' '.join(t))

    for w, p, trans in lexicon:
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

    with open(str(output_dir / 'phones.txt'), 'w', encoding='utf-8') as f:
        for p, i in phone_map.items():
            f.write(f'{p} {i}\n')

    counter = 0
    words_map = {}
    words_map['<eps>'] = counter
    counter += 1
    wordlist = set()
    for w, p, t in lexicon:
        wordlist.add(w)
    for w in sorted(wordlist):
        words_map[w] = counter
        counter += 1
    words_map['#0'] = counter
    counter += 1
    words_map['<s>'] = counter
    counter += 1
    words_map['</s>'] = counter

    with open(str(output_dir / 'words.txt'), 'w', encoding='utf-8') as f:
        for w, i in words_map.items():
            f.write(f'{w} {i}\n')

    with open(str(output_dir / 'trans.int'), 'w', encoding='utf-8') as f:
        for id, trans in transcription.items():
            f.write(id)
            for w in trans:
                f.write(f' {words_map[w]}')
            f.write('\n')

    with open(str(output_dir / 'word_boundary.int'), 'w', encoding='utf-8') as f:
        cnt = 1
        for i in range(len(silence_phones)):
            for b in ['nonword', 'begin', 'end', 'singleton', 'internal']:
                f.write(f'{cnt} {b}\n')
                cnt += 1
        for i in range(len(nonsilence_phones)):
            for b in ['begin', 'end', 'singleton', 'internal']:
                f.write(f'{cnt} {b}\n')
                cnt += 1

    kaldi.make_L_fst(lexicon, output_dir / 'L_unsorted.fst', optional_silence, output_dir / 'phones.txt',
                     output_dir / 'words.txt')

    kaldi.fstarcsort(output_dir / 'L_unsorted.fst', output_dir / 'L.fst')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('text')
    parser.add_argument('output_dir')
    parser.add_argument('--oov-word', default='<unk>')
    parser.add_argument('--g2p-model', default='data/g2p/model.fst')
    parser.add_argument('--g2p-lexicon', default='data/g2p/lexicon.txt')
    parser.add_argument('--kaldi-root', default='/home/guest/Applications/kaldi')

    args = parser.parse_args()

    kaldi = KaldiPrograms(args.kaldi_root)

    text_path = Path(args.text)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    g2p_path = Path(args.g2p_model)
    g2p_lex_path = Path(args.g2p_lexicon)
    oov = args.oov_word

    prepare_language_file(text_path, output_dir, g2p_path, g2p_lex_path, oov, kaldi)
