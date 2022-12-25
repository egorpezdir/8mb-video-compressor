

#script to convert video files to specific size

DEFAULT_SIZE = 7.9 # MiB
DEFAULT_AUDIORATE = 96 # Kbit/s
DEFAULT_PRESET = 'slower'

import argparse as ap
import subprocess as sub
import pathlib as pl
import os
import re
import sys
import time
from math import floor

parser = ap.ArgumentParser(description='Compress video to specific size.')
parser.add_argument('--size', '-s', type=float, default=DEFAULT_SIZE,
                   help=f'Target filesize in MiB. (def. {DEFAULT_SIZE})')
parser.add_argument('--audio', '-a', type=int, default=DEFAULT_AUDIORATE, metavar='RATE',
                   help=f'Target audio bitrate in Kbit/s. (def. {DEFAULT_AUDIORATE})')
parser.add_argument('--preset', '-p', type=str, default=DEFAULT_PRESET,
                   help=f'ffmpeg preset. (def. {DEFAULT_PRESET})')
parser.add_argument('--tune', '-t', type=str, help=f'ffmpeg tune.')
parser.add_argument('--output', '-o', type=str, metavar='FILE', help='Output file.')
parser.add_argument('--nodelete', '-n', action='store_false', help='Prevent deletion prompt.')
parser.add_argument('--nofast', action='store_false', help='Disable fast start flag.')
parser.add_argument('input', type=str, metavar='FILE', help='Input file.')

args = parser.parse_args()

def mb_to_kbit(mb):
    return mb * 8192

wanted_size = mb_to_kbit(args.size)
audio_rate = args.audio
audio_rate_str = f"{audio_rate}k"
preset = args.preset
tune = args.tune
input_file = args.input

def default_output_file(target):
    target_path = pl.PurePath(target)
    suffix = target_path.suffix
    return str(target_path.with_suffix(f".8mb{suffix}"))

output_file = args.output or default_output_file(input_file)
prompt_deletion = args.nodelete
faststart = args.nofast

probe = sub.run(['ffprobe', '-i', input_file, '-show_format', '-v', 'quiet'],
        stdout=sub.PIPE)
if probe.returncode:
    print(f"ffprobe exited with code {probe.returncode}.", file=sys.stderr)
    exit()

duration = float(re.search('duration=(.*?)$', probe.stdout.decode('utf-8'), re.M).group(1))
target_rate = f"{floor(wanted_size / duration - audio_rate)}k"

start = time.time()

common = ['ffmpeg', '-i', input_file, '-c:v', 'libx264', '-preset', preset, '-b:v', target_rate]
firstopts = ['-y', '-pass', '1', '-vsync', 'cfr', '-f', 'null', '/dev/null']
secondopts = ['-pass', '2', '-c:a', 'aac', '-b:a', audio_rate_str, output_file]

if tune is not None:
    common += ['-tune', tune]

if faststart:
    common += ['-movflags', '+faststart']

# first pass

firstpass = sub.run(common + firstopts)
if firstpass.returncode:
    print(f"First pass exited with code {probe.returncode}.", file=sys.stderr)
    exit()

# second pass

secondpass = sub.run(common + secondopts)
if secondpass.returncode:
    print(f"Second pass exited with code {probe.returncode}.", file=sys.stderr)
    exit()

# final output

elapsed = time.time() - start

probe = sub.run(['ffprobe', '-i', output_file, '-show_format', '-v', 'quiet'])
if probe.returncode:
    print(f"ffprobe exited with code {probe.returncode}.", file=sys.stderr)

minutes = floor(elapsed / 60)
seconds = floor(elapsed % 60)
print(f"Elapsed time: {minutes}m {seconds}s")

os.system("del *.mbtree && del *.log")
