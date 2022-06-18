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


def parse_args():
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

    return parser.parse_args()


def main():
    '''Main program'''
    args = parse_args()

    # main parser actions
    if args.verbose:
        global DEBUG_ZIPPEY
        DEBUG_ZIPPEY = True

    init()

    input = io.open(sys.stdin.fileno(), 'rb')
    output = io.open(sys.stdout.fileno(), 'wb')

    # command switch
    if args.func == 'e':
        encode(input, output)
    elif args.func == 'd':
        decode(input, output)


if __name__ == '__main__':
    main()
