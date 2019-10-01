from typing import List
import struct
import re
from subprocess import Popen, PIPE


class AlignPipe:
    def __init__(self, tree, model, lda, lex, words, phones, boundaries, disambig, transition_scale=1.0,
                 acoustic_scale=0.1, self_loop_scale=0.1, beam=20, retry_beam=300, careful=False):
        self.proc = Popen(['gmm-align-pipe', f'--transition-scale={transition_scale}', f'--acoustic-scale={acoustic_scale}',
                           f'--self-loop-scale={acoustic_scale}', f'--beam={beam}', f'--retry-beam={retry_beam}',
                           f'--careful={str(careful).lower()}', f'--phone-symbols={phones}', 
                           str(tree), str(model), str(lda), str(lex), str(words),
                           str(boundaries), str(disambig)], stdin=PIPE, stdout=PIPE)

        token = self.proc.stdout.readline().strip().decode()
        assert token == 'RDY', 'Token missing error! '+token

    def process_segment(self, audio: bytes, trans: str) -> tuple:
        self.proc.stdin.write(struct.pack('<i', int(len(audio)/2)))
        self.proc.stdin.write(audio)
        self.proc.stdin.write(struct.pack('<i', 0))
        trans=trans.encode('utf-8')
        self.proc.stdin.write(struct.pack('<i', len(trans)))
        self.proc.stdin.write(trans)

        self.proc.stdin.flush()

        print('sent')

        head_num = self.proc.stdout.readline().strip().decode().split()
        nw = 0
        np = 0
        if len(head_num) == 2 and head_num[0] == 'NW':
            nw = int(head_num[1])
            np = 0
        elif len(head_num) == 4 and head_num[0] == 'NW' and head_num[2] == 'NP':
            nw = int(head_num[1])
            np = int(head_num[3])
        else:
            raise RuntimeError(f'KALDI ENGINE HEADER ERROR: {head_num}')

        words = []
        for i in range(nw):
            line = self.proc.stdout.readline().strip().decode()
            tok = line.split()
            assert len(tok) == 4 and tok[0] == 'W', 'KALDI ENGINE WORD LINE ERROR: '+line
            words.append((tok[1], float(tok[2]), float(tok[3])))

        phones = []
        for i in range(np):
            line = self.proc.stdout.readline().strip().decode()
            tok = line.split()
            assert len(
                tok) == 4 and tok[0] == 'P', 'KALDI ENGINE PHONE LINE ERROR: '+line
            phones.append((tok[1], float(tok[2]), float(tok[3])))

        return words, phones

    def close(self):

        self.proc.stdin.write(struct.pack('i', 0))
        self.proc.stdin.write(struct.pack('i', 0))
        self.proc.stdin.close()
        self.proc.stdout.close()
