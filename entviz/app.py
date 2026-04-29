from argparse import ArgumentParser
import re
import sys

from .pipeline import render

ASPECT_RATIO_PAT = re.compile(r'(\d+):(\d+)')


def main():
    parser = ArgumentParser(
        prog='entviz',
        description='Visualize entropy as an SVG file.')
    parser.add_argument('entropy')
    parser.add_argument('--ar', '--aspectratio', metavar='RATIO', default='1:1')
    parser.add_argument('--fs', '--fontsize', metavar='POINT', default=12, type=int)
    parser.add_argument('-o', '--output', metavar='FILE', default=None,
                        help='Write SVG to FILE (default: stdout)')
    args = parser.parse_args()

    ar_width, ar_height = 1, 1
    if args.ar:
        match = ASPECT_RATIO_PAT.match(args.ar)
        if match:
            ar_width, ar_height = map(int, match.groups())
            if ar_width < 1 or ar_height < 1 or ar_width > 100 or ar_height > 100:
                parser.error('Invalid aspect ratio.')

    font_size_pt = args.fs
    if font_size_pt < 6 or font_size_pt > 30:
        parser.error('Invalid font size.')

    target_ar = ar_width / ar_height
    svg = render(args.entropy, target_ar=target_ar, font_size_pt=font_size_pt)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(svg)
    else:
        sys.stdout.write(svg)
        sys.stdout.write('\n')


if __name__ == '__main__':
    main()
