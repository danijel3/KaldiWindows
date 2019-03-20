import argparse
import sys
from xml.etree import ElementTree
from zipfile import ZipFile


def convert_ant_segments(ant_file, segments_file, text_file):
    with ZipFile(ant_file) as zip:
        with zip.open('annotation.xml',encoding='utf-8') as f:
            annot = ElementTree.parse(f).getroot()

    ns = {'a': 'http://tempuri.org/AnnotationSystemDataSet.xsd'}

    el = annot.find("a:Layer[a:Name='phrase']", ns)
    phrase_id = el.find('a:Id', ns).text

    print(f'Found phrase layer id: {phrase_id}', file=sys.stderr)

    el = annot.find("a:Configuration[a:Key='Samplerate']", ns)
    samplerate = float(el.find('a:Value', ns).text)

    print(f'Sample rate: {samplerate}', file=sys.stderr)

    segments = []
    for el in annot.findall(f"a:Segment[a:IdLayer='{phrase_id}']", ns):
        text = el.find('a:Label', ns).text
        start = float(el.find('a:Start', ns).text) / samplerate
        start = round(start, 2)
        length = float(el.find('a:Duration', ns).text) / samplerate
        end = round(start + length, 2)
        segments.append((text, start, end))

    segments = sorted(segments, key=lambda x: x[1])

    print(f'Found {len(segments)} segments.', file=sys.stderr)

    with open(segments_file, 'w',encoding='utf-8') as f:
        with open(text_file, 'w',encoding='utf-8') as g:
            for num, seg in enumerate(segments):
                f.write(f'seg_{num:03} input {seg[1]:0.2f} {seg[2]:0.2f}\n')
                g.write(f'seg_{num:03} {seg[0]}\n')

    print('Done', file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ant')
    parser.add_argument('segments')
    parser.add_argument('text')

    args = parser.parse_args()

    convert_ant_segments(args.ant, args.segments, args.text)
