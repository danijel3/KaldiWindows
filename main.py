import argparse
import sys
from pathlib import Path
from shutil import move, copy

from utils.apply_mapping import apply_mapping
from utils.convert_ant_segments import convert_ant_segments
from utils.fix_ctms import fix_ctms
from utils.kaldi_programs import KaldiPrograms
from utils.prepare_language import prepare_language_file

if getattr(sys, 'frozen', False):
    prog_root = Path(sys.executable).parent
else:
    prog_root = Path(__file__).parent

work = prog_root / 'work'
data = prog_root / 'data'
model_dir = data / 'model'
g2p_dir = data / 'g2p'

custom_phones = data / 'custom_phones.txt'
lda_mat = model_dir / 'final.mat'
model_file = model_dir / 'final.mdl'
tree = model_dir / 'tree'
g2p_path = g2p_dir / 'model.fst'
g2p_lex_path = g2p_dir / 'lexicon.txt'

if sys.platform == 'win32' or sys.platform == 'cygwin':
    def_bin = prog_root / 'win32bin'
    import win_unicode_console

    win_unicode_console.enable()
else:
    def_bin = '/home/guest/Applications/kaldi'

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('audio', type=Path, help='Audio WAV file.')
    parser.add_argument('trans', type=Path, help='Transcription file.')
    parser.add_argument('--type', '-t', default='ant',help='Type of transcription: ant (ANT xml transcription and segmentation), txt (text transcription)')
    parser.add_argument('--bin-root', type=Path, help='Root folder containing all the binary files', default=def_bin)
    parser.add_argument('--cleanup', type=str, default='y', help='Erase unnecessary files after completion.')

    args = parser.parse_args()

    kaldi = KaldiPrograms(args.bin_root)

    work.mkdir(exist_ok=True)

    segments = work / 'segments'
    text_file = work / 'text'

    if args.type=='ant':
        convert_ant_segments(args.trans, segments, text_file)
    elif args.type=='txt':
        with open(str(args.trans)) as f, open(str(text_file),'w') as g:
            l=f.readline().strip()
            g.write('input '+l+'\n')                
        segments=None
    else:
        print('Unknown type!')
        exit(1)

    with open(work / 'wav.scp', 'w', encoding='utf-8') as f:
        wav_file = Path(args.audio)
        f.write(f'input {wav_file}\n')

    kaldi.compute_mfcc_feats(work / 'wav.scp', work / 'mfcc', segments)
    kaldi.compute_cmvn_stats(work / 'mfcc', work / 'cmvn')

    feature_pipeline = f'ark,s,cs:apply-cmvn ark:"{work / "cmvn"}" ark:"{work / "mfcc"}" ark:- | ' \
        f'splice-feats --left-context=3 --right-context=3 ark:- ark:- | ' \
        f'transform-feats "{lda_mat}" ark:- ark:- |'

    output_pipeline = f'ark:|linear-to-nbest ark:- ark:"{work / "trans.int"}" "" "" ark:- | ' \
        f'lattice-align-words "{work / "word_boundary.int"}" "{model_file}" ark:- ark:"{work / "nbest_ali"}"'

    prepare_language_file(text_file, work, g2p_path, g2p_lex_path, '<unk>', kaldi)

    kaldi.gmm_align(tree, model_file, work / 'L.fst', feature_pipeline, work / 'trans.int', output_pipeline)

    kaldi.nbest_to_ctm(work / 'nbest_ali', work / 'ctm.int')

    kaldi.lattice_to_phone_lattice(model_file, work / 'nbest_ali', work / 'phone_ali')
    kaldi.nbest_to_ctm(work / 'phone_ali', work / 'phone_ctm.int')

    apply_mapping(work / 'ctm.int', work / 'words.txt', '4', work / 'ctm.txt', True)
    apply_mapping(work / 'phone_ctm.int', work / 'phones.txt', '4', work / 'phone_ctm.txt', True)

    phone_map = {}
    with open(str(custom_phones), encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            if len(tok) == 1:
                phone_map[tok[0]] = ''
            elif len(tok) == 2:
                phone_map[tok[0]] = tok[1]

    with open(work / 'phone_ctm.txt', encoding='utf-8') as f:
        with open(work / 'phone_ctm_fixed.txt', 'w', encoding='utf-8') as g:
            for l in f:
                tok = l.strip().split()
                ph = tok[-1]
                if ph[-2] == '_' and (ph[-1] == 'B' or ph[-1] == 'E' or ph[-1] == 'S' or ph[-1] == 'I'):
                    ph = ph[:-2]
                if ph in phone_map:
                    ph = phone_map[ph]
                tok[-1] = ph
                g.write(' '.join(tok))
                g.write('\n')

    if segments:
        fix_ctms(work / 'ctm.txt', segments, work / 'tmp')
        move(work / 'tmp', work / 'ctm.txt')
        fix_ctms(work / 'phone_ctm_fixed.txt', segments, work / 'tmp')
        move(work / 'tmp', work / 'phone_ctm_fixed.txt')

    with open(work / 'ctm.txt', encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            print(f'w\t{tok[2]}\t{tok[3]}\t{tok[4]}')

    with open(work / 'phone_ctm_fixed.txt', encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            if len(tok) >= 5:
                print(f'p\t{tok[2]}\t{tok[3]}\t{tok[4]}')

    if args.cleanup.lower() in ['y','yes','t','true']:
        for file in work.glob('**/*'):
            file.unlink()

    kaldi.close()
