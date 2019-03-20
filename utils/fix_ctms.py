def fix_ctms(input_ctm, segments, output_ctm):
    segs = {}
    with open(str(segments),encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            assert len(tok) == 4
            segs[tok[0]] = tok[1:]

    with open(str(input_ctm),encoding='utf-8') as f:
        with open(str(output_ctm), 'w',encoding='utf-8') as g:
            for l in f:
                tok = l.strip().split()
                seg = segs[tok[0]]
                start = float(tok[2]) + float(seg[1])
                start = round(start, 2)
                length = float(tok[3])
                length = round(length, 2)
                g.write(f'{seg[0]} {tok[1]} {start:0.2f} {length:0.2f}')
                if len(tok) > 4:
                    g.write(f' {tok[4]}')
                g.write('\n')
