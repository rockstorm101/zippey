#!/usr/bin/env python
#
#  Copyright (c) 2014, Sippey Fun Lab
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
#  DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDER BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

#
# Zippey is a Git filter for friendly handling of ZIP-based files.
# This is the main source file.
# See the README for further details.
#
# Author: Sippey (sippey@gmail.com)
# Date: Apr.18, 2014
#
# Modified by Kristian Hoey Horsberg <khh1990 ' at ' gmail.com>
# to make python 3 compatible
# Date May 20th 2014
#
#  Modified 2015-04-30 by jpnp to detect an already zipped file
#     when decoding
#

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
    '''Encode into special VCS friendly format from input to output'''
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
    '''Decode from special VCS friendly format from input to output'''
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

def main():
    '''Main program'''
    init()

    input = io.open(sys.stdin.fileno(), 'rb')
    output = io.open(sys.stdout.fileno(), 'wb')

    if len(sys.argv) < 2 or sys.argv[1] == '-' or sys.argv[1] == '--help':
        sys.stdout.write(("{}\n"
                "To encode: 'python zippey.py e'\n"
                "To decode: 'python zippey.py d'\n"
                "All files read from stdin and printed to stdout\n")
                .format(NAME))
    elif sys.argv[1] == 'e':
        encode(input, output)
    elif sys.argv[1] == 'd':
        decode(input, output)
    else:
        error("Illegal argument '{}'. Try --help for more information".format(sys.argv[1]))
        sys.exit(1)

if __name__ == '__main__':
    main()
