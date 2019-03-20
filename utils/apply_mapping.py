import argparse
import sys


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


def apply_mapping(input, mapping, field, output, flip=False, blank=False):
    map = {}
    with open(mapping, encoding='utf-8') as f:
        for l in f:
            tok = l.strip().split()
            assert len(tok) == 2
            map[tok[0]] = tok[1]

    if flip:
        map = {v: k for k, v in map.items()}

    if input == '-':
        f = sys.stdin
    else:
        f = open(input, encoding='utf-8')
    if output == '-':
        g = sys.stdout
    else:
        g = open(output, 'w', encoding='utf-8')

    for l in f:
        tok = l.strip().split()
        for fi in range2fields(field, len(tok)):
            if blank and tok[fi] not in map:
                tok[fi] = ''
            else:
                tok[fi] = str(map[tok[fi]])
        g.write(' '.join(tok) + '\n')

    f.close()
    g.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--field')
    parser.add_argument('-x', '--flip', action='store_true')
    parser.add_argument('-b', '--blank', action='store_true', help='Use blank for missing values.')
    parser.add_argument('mapping')
    parser.add_argument('input')
    parser.add_argument('output')

    args = parser.parse_args()

    apply_mapping(args.input, args.mapping, args.field, args.output, args.flip)
