#!/usr/bin/env python
#
#  Copyright (c) 2014 - 2019, Sippey Fun Lab <sippey@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the Sippey Fun Lab nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL Sippey Fun Lab BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# This is the BSD 3-clause "New" or "Revised" license (bsd-3-clause).
#

#
# Zippey is a Git filter for friendly handling of ZIP-based files.
# This is the main source file.
# See the README for further details.
#

import argparse
import zipfile
import sys
import io
import base64
import string
import tempfile
import os.path
import shutil
import subprocess

DEBUG_ZIPPEY = False
NAME = 'Zippey'
ENCODING = 'UTF-8'


def debug(msg):
    '''Print debug message'''
    if DEBUG_ZIPPEY:
        sys.stderr.write('{0}: debug: {1}\n'.format(NAME, msg))

def error(msg):
    '''Print error message'''
    sys.stderr.write('{0}: error: {1}\n'.format(NAME, msg))

def init():
    '''Initialize writing; set binary mode for windows'''
    debug("Running on {}".format(sys.platform))
    if sys.platform.startswith('win'):
        import msvcrt
        debug("Enable Windows binary workaround")
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

def encode(input, output):
    '''Encode into special VCS friendly format from input (application/zip) to output (text/plain)'''
    debug("ENCODE was called")
    tfp = tempfile.TemporaryFile(mode='w+b')
    tfp.write(input.read())
    zfp = zipfile.ZipFile(tfp, "r")
    for name in zfp.namelist():
        data = zfp.read(name)
        text_extentions = ['.txt', '.html', '.xml']
        extention = os.path.splitext(name)[1][1:].strip().lower()
        try:
            # Check if text data
            data.decode(ENCODING)
            try:
                strdata = map(chr, data)
            except TypeError:
                strdata = data
            if extention not in text_extentions and not all(c in string.printable for c in strdata):
                raise UnicodeDecodeError(ENCODING, "".encode(ENCODING), 0, 1, "Artificial exception")

            # Encode
            debug("Appending text file '{}'".format(name))
            output.write("{}|{}|A|{}\n".format(len(data), len(data), name).encode(ENCODING))
            output.write(data)
            output.write("\n".encode(ENCODING)) # Separation from next meta line
        except UnicodeDecodeError:
            # Binary data
            debug("Appending binary file '{}'".format(name))
            raw_len = len(data)
            data = base64.b64encode(data)
            output.write("{}|{}|B|{}\n".format(len(data), raw_len, name).encode(ENCODING))
            output.write(data)
            output.write("\n".encode(ENCODING))  # Separation from next meta line
    zfp.close()
    tfp.close()

def decode(input, output):
    '''Decode from special VCS friendly format from input (text/plain) to output (application/zip)'''
    debug("DECODE was called")

    # Check whether already zipped
    if (input.peek(4)[0:4] == b'PK\003\004'):
        debug("Already zipped - copying directly")
        shutil.copyfileobj(input, output)
        return

    tfp = tempfile.TemporaryFile(mode='w+b')
    zfp = zipfile.ZipFile(tfp, "w", zipfile.ZIP_DEFLATED)

    while True:
        meta = input.readline().decode(ENCODING)
        if not meta:
            break

        (data_len, raw_len, mode, name) = [t(s) for (t, s) in zip((int, int, str, str), meta.split('|'))]
        if mode == 'A':
            debug("Appending text file '{}'".format(name))
            zfp.writestr(name.rstrip(), input.read(data_len))
            input.read(1) # Skip last '\n'
        elif mode == 'B':
            debug("Appending binary file '{}'".format(name.rstrip()))
            zfp.writestr(name.rstrip(), base64.b64decode(input.read(data_len)))
            input.read(1) # Skip last '\n'
        else:
            # Should never reach here
            zfp.close()
            tfp.close()
            error('Illegal mode "{}"'.format(mode))
            sys.exit(1)

    # Flush all writes
    zfp.close()

    # Write output
    tfp.seek(0)
    output.write(tfp.read())
    tfp.close()


def install(args):
    '''Install Git filters'''

    debug("Install was called")

    config_cmd = ["git", "config"]
    if args.global_:
        debug("Filters will be installed globally")
        config_cmd.append("--global")
    else:
        debug("Filters will be installed locally")

    # If there is no '.git' folder -> exit
    if not args.global_ and not os.path.isdir(".git"):
        error("Attempted local install but missing git repository")
        sys.exit(1)

    # Install the add/commit filter
    subprocess.run(
        config_cmd + ["filter.zipfilter.clean", "zippey.py -v e"],
        check=True)

    # Install the checkout filter
    subprocess.run(
        config_cmd + ["filter.zipfilter.smudge", "zippey.py -v d"],
        check=True)

    # Install the diff filter
    if args.diff:
        debug("Installing diff filters")
        subprocess.run(
            config_cmd + ["diff.zipfilter.textconv", "zippey.py textconv"],
            check=True)

    _install_attributes(args)


def _install_attributes(args):

    if args.global_:
        error("Global installation of Git attributes is not supported")
        error("This operation requires manual interaction")
        return

    attr_file = ".git/info/attributes"

    # If the attributes file already exists, remove it
    # We don't want to do this on a global file
    if os.path.isfile(attr_file):
        debug(f"File '{attr_file}' pruned")
        os.remove(attr_file)

    if args.diff:
        diff_filter = "diff=zipfilter"
    else:
        diff_filter = ""

    with open(attr_file, "w") as tmp_file:
        tmp_file.write(f"# File automatically generated by {NAME}.\n")
        for ext in args.ext:
            debug(f"Adding attribute for filtering '.{ext}' files")
            tmp_file.write(f"*.{ext:8}  filter=zipfilter  {diff_filter}\n")


def textconv(args):
    '''Summarise files and sizes within a ZIP file'''
    debug("Textconv was called")

    if not zipfile.is_zipfile(args.file_):
        error(f"File '{args.file_}' is not a ZIP file")
        sys.exit(1)

    name_len = 30
    size_len = 10
    lines = [f"{'File Name':^{name_len}}  {'Size':^{size_len}}"]
    lines.append(f"{'-':->{name_len}}  {'-':-<{size_len}}")

    with zipfile.ZipFile(args.file_) as zfile:
        for item in zfile.infolist():
            name = item.filename
            if len(name) > name_len:
                sname = ('...' + name[len(name)-name_len+3:])
            else:
                sname = name
                lines.append(f"{sname:>{name_len}}  "
                             f"{item.file_size:{size_len}}")

    with open(args.output, 'w') as output:
        for line in lines:
            output.write(f"{line}\n")


def parse_args():
    '''Parse command line arguments'''

    # main parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="show debug info")
    command_parsers = parser.add_subparsers(required=True,
                                            metavar="command")

    # encode command parser
    e_desc = "Files are read from stdin and printed to stdout."
    e_parser = command_parsers.add_parser('encode', aliases=['e'],
                                          help="encode from ZIP to text",
                                          description=e_desc)
    e_parser.set_defaults(func='e')

    # decode command parser
    d_parser = command_parsers.add_parser('decode', aliases=['d'],
                                          help="decode from text to ZIP",
                                          description=e_desc)
    d_parser.set_defaults(func='d')

    # install command parser
    i_parser = command_parsers.add_parser('install',
                                          help="install Git filters")
    i_parser.add_argument('--global', action='store_true', dest='global_',
                          help="install filters globally")
    i_parser.add_argument('--diff', action='store_true',
                          help="install a simplified diff filter")
    i_parser.add_argument('--ext', nargs='+',
                          help="extension(s) to install filters for",
                          default=['docx', 'xlsx', 'pptx',
                                   'odt',
                                   'jar',
                                   'FCStd'])
    i_parser.set_defaults(func=install)

    # textconv command parser
    textconv_help = "convert to content list suitable for diff-ing"
    t_parser = command_parsers.add_parser('textconv', help=textconv_help)
    t_parser.add_argument('file_', metavar='FILE',
                          help="ZIP file to print information from")
    t_parser.set_defaults(func=textconv)

    return parser.parse_args()


def main():
    '''Main program'''
    args = parse_args()

    # main parser actions
    if args.verbose:
        global DEBUG_ZIPPEY
        DEBUG_ZIPPEY = True

    init()

    # command switch
    if args.func in ['e', 'd']:
        with io.open(sys.stdin.fileno(), 'rb') as in_stream,\
             io.open(sys.stdout.fileno(), 'wb') as out_stream:
            if args.func == 'e':
                encode(in_stream, out_stream)
            elif args.func == 'd':
                decode(in_stream, out_stream)
    else:
        args.output = sys.stdout.fileno()
        args.func(args)


if __name__ == '__main__':
    main()
