import argparse
import sys
from pathlib import Path
from shutil import move, copy
import wave

from utils.apply_mapping import apply_mapping
from utils.convert_ant_segments import process_ant_segments
from utils.fix_ctms import fix_ctms
from utils.kaldi_programs import KaldiPrograms
from utils.prepare_language import prepare_language_wordlist, prepare_language_file
from utils.align_pipe import AlignPipe

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
    parser.add_argument('--type', '-t', default='ant',
                        help='Type of transcription: ant (ANT xml transcription and segmentation), txt (text transcription)')
    parser.add_argument('--bin-root', type=Path,
                        help='Root folder containing all the binary files', default=def_bin)
    parser.add_argument('--cleanup', type=str, default='y',
                        help='Erase unnecessary files after completion.')

    args = parser.parse_args()

    kaldi = KaldiPrograms(args.bin_root)

    work.mkdir(exist_ok=True)

    with wave.open(str(args.audio)) as f:
        assert f.getframerate() == 16000, 'Wrong audio framerate! '+str(f.getframerate())
        assert f.getsampwidth() == 2, 'Wrong sample size!'
        assert f.getnchannels() == 1, 'Only support mono!'
        samp_num = f.getnframes()
        audio = f.readframes(samp_num)

    if args.type == 'ant':
        segments = process_ant_segments(args.trans)
        wordlist = set()
        for seg in segments:
            wordlist.add(seg[0])
        prepare_language_wordlist(wordlist, None, work, g2p_path,
                                  g2p_lex_path, '<unk>', kaldi)
    elif args.type == 'txt':
        wordlist = set()
        with open(args.trans,encoding='utf-8') as f:
            for l in f:
                for w in l.strip().split():
                    wordlist.add(w)
        print(wordlist)
        prepare_language_wordlist(wordlist, None, work, g2p_path,
                                  g2p_lex_path, '<unk>', kaldi)

    pipe = AlignPipe(tree, model_file, lda_mat, work / 'L.fst', work /
                     'words.txt', work / 'phones.txt', work / 'word_boundary.int', work / 'phones' / 'disambig.int')

    if args.type == 'ant':
        for seg in segments:
            start_samp = int(seg[1]*16000.0)*2
            end_samp = start_samp+int(seg[2]*16000.0)*2
            seg_audio = audio[start_samp:end_samp]
            seg_trans = seg[0]
            seg_w, seg_p = pipe.process_segment(seg_audio, seg_trans)
            for w, s, l in seg_w:
                print(f'W {w} {s} {l}')
            for p, s, l in seg_p:
                print(f'P {p} {s} {l}')
    elif args.type == 'txt':
        with open(str(args.trans), encoding='utf-8') as f:
            trans = f.readline().strip()
        seg_w, seg_p = pipe.process_segment(audio, trans)
        for w, s, l in seg_w:
            print(f'W {w} {s} {l}')
        for p, s, l in seg_p:
            print(f'P {p} {s} {l}')

    if args.cleanup.lower() in ['y', 'yes', 't', 'true']:
        for file in work.glob('**/*'):
            if file.is_file():
                file.unlink()

    kaldi.close()
    pipe.close()
