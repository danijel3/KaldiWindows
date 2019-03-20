import os
import sys
from pathlib import Path
from subprocess import run, DEVNULL, Popen, PIPE

from utils.make_lexicon_fst import write_fst_with_silence

progs = ['compute-mfcc-feats', 'compute-cmvn-stats', 'apply-cmvn', 'splice-feats', 'transform-feats', 'linear-to-nbest',
         'lattice-align-words', 'nbest-to-ctm', 'gmm-align', 'phonetisaurus-g2pfst', 'fstcompile', 'fstarcsort',
         'lattice-to-phone-lattice', 'extract-segments']


class KaldiPrograms:

    def __init__(self, root_path):
        self.root = Path(root_path)
        self.paths = set()
        for prog in progs:
            p = list(self.root.glob(f'**/{prog}'))
            if len(p) == 0:
                p = list(self.root.glob(f'**/{prog}.exe'))
            if len(p) == 0:
                raise RuntimeError(f'Cannot find {prog} in path {self.root}!')
            self.paths.add(str(p[0].parent))

        for path in self.paths:
            print(f'Adding to path: {path}', file=sys.stderr)

        path_env = set(os.environ['PATH'].split(os.pathsep))
        path_env.update(self.paths)
        os.environ['PATH'] = os.pathsep.join(path_env)

    def compute_mfcc_feats(self, wav_scp, mfcc, segments=None):
        if segments:
            seg = Popen(['extract-segments', f'scp:{wav_scp}', str(segments), 'ark:-'], stdout=PIPE)
            mfcc = Popen(['compute-mfcc-feats', f'ark:-', f'ark:{mfcc}'], stdin=seg.stdout)
            mfcc.communicate()
            seg.stdout.close()
            assert mfcc.returncode == 0, f'Process compute-mfcc-feats returned code {mfcc.returncode}'
        else:
            run(['compute-mfcc-feats', f'scp:{wav_scp}', f'ark:{mfcc}'], check=True)

    def compute_cmvn_stats(self, mfcc, cmvn):
        run(['compute-cmvn-stats', f'ark:{mfcc}', f'ark:{cmvn}'], check=True)

    def gmm_align(self, tree, model, lex, feature_pipeline, trans, output_pipeline, transition_scale=1.0,
                  acoustic_scale=0.1, self_loop_scale=0.1, beam=20, retry_beam=300, careful=False):

        run(['gmm-align', f'--transition-scale={transition_scale}', f'--acoustic-scale={acoustic_scale}',
             f'--self-loop-scale={acoustic_scale}', f'--beam={beam}', f'--retry-beam={retry_beam}',
             f'--careful={str(careful).lower()}', str(tree), str(model), str(lex), feature_pipeline, f'ark:{trans}',
             output_pipeline], check=True)

    def nbest_to_ctm(self, nbest, ctm, frame_shift=0.01, print_silence=False):
        run(['nbest-to-ctm', f'--frame-shift={frame_shift}', f'--print-silence={str(print_silence).lower()}',
             f'ark:{nbest}', str(ctm)], check=True)

    def lattice_to_phone_lattice(self, model, lattice, phone_lattice):
        run(['lattice-to-phone-lattice', str(model), f'ark:{lattice}', f'ark:{phone_lattice}'], check=True)

    def phonetisaurus_g2p(self, model, wordlist, output):
        with open(str(output), 'w', encoding='utf-8') as f:
            run(['phonetisaurus-g2pfst', '--pmass=0.8', '--nbest=10', f'--model={model}', f'--wordlist={wordlist}'],
                stdout=f, stderr=DEVNULL, check=True)

    def make_L_fst(self, lexicon, output_fst, optional_silence, phones_file, words_file):
        proc_compile = Popen(
            ['fstcompile', f'--isymbols={phones_file}', f'--osymbols={words_file}',
             '--keep_isymbols=false', '--keep_osymbols=false', '-', str(output_fst)],
            stdin=PIPE, stdout=PIPE, encoding='utf-8')

        write_fst_with_silence(lexicon, 0.5, optional_silence, None, nonterminals=None, left_context_phones=None,
                               file=proc_compile.stdin)

        proc_compile.communicate()
        proc_compile.stdin.close()

        assert proc_compile.returncode == 0, f'Process fstcompile returned code {proc_compile.returncode}'

    def fstarcsort(self, input_fst, output_fst):
        run(['fstarcsort', '--sort_type=olabel', str(input_fst), str(output_fst)], check=True)
