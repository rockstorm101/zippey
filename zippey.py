#!/usr/bin/env python

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
#  Zippey: A Git filter for friendly handling of ZIP-based files
#
#  There are many types of ZIP-based files, such as  Microsoft Office .docx,
#  .xlsx, .pptx files, OpenOffice .odt files and jar files, that contains 
#  plaintext content but not really tractable by git due to compression smears
#  parts that have been modified and parts that remain the same across commit.
#  This prevent Git from versioning these files and treat them as a new binary
#  blob every time the file is saved. 
#
#  Zippey is a Git filter that un-zip zip-based file into a simple text format
#  during git add/commit ("clean" process) and recover the original zip-based 
#  file after git checkout ("smudge" process). Since diff is taken on the 
#  "cleaned" file after file is added, it is likely real changes to file can be 
#  reflected by original git diff command. 
#
#  The text format is defined as a series of records. Each records represent a
#  file in the original zip-based file, which is composed of two parts,
#  a header that contains meta file and a body that contains data. The header
#  is a few data fields segmented by pipe character like this:
#
#       length|raw_length|type|filename
#
#  where length is an ascii coded integer of the following data section, raw_length
#  is the orginal length of data (if transformation is taken), type can be A for 
#  text data or B for binary data, and filename is the original file name 
#  including path if the zip-based file contains directories. Immediately after
#  the header, there is a carriage return ('\n'), follows "length" byte of 
#  data, and then another CR and then the next recor, i,e,
#
#       [header1]\n[data1]\n[header2]\n[data2] ...
#
#  There are two types of data section. If the file contains only text data, 
#  its content is copied to data section without any change, otherwise, data 
#  is base64 coded to ensure the entire file is text format.
#
#  
#  Author: Sippey (sippey@gmail.com)
#  Date: Apr.18, 2014
#
#
  
import zipfile
import sys
import base64
import string
import tempfile
import os.path

DEBUG_ZIPPEY=False;


def print_msg(msg):
    if DEBUG_ZIPPEY:
        sys.stderr.write('Zippey Message:%s\n' % (msg));


list_text = ['.txt','.html','.xml'];

#print sys.argv[1];

if sys.platform.startswith('win'):
    import msvcrt
    msvcrt.setmode (sys.stdin.fileno(), os.O_BINARY);
    msvcrt.setmode (sys.stdout.fileno(), os.O_BINARY);
    

inputt = sys.stdin;
output = sys.stdout;

fp = tempfile.TemporaryFile();

if sys.argv[1]=='e':
    print_msg("ENCODE is called");

    fp.write(sys.stdin.read());
    
    file=zipfile.ZipFile(fp, "r");

    for name in file.namelist():
        data = file.read(name);
        ext_name = os.path.splitext(name)[1][1:].strip().lower();
        
        # shortcut to avoid testing entire content of files
        is_text= (ext_name in list_text) or all(c in string.printable for c in data);

        if is_text:
            output.write("%d|%d|A|%s\n" % (len(data),len(data), name));
            output.write(data);
            output.write("\n");  # separation from next meta line
        else:
            # is binary
            raw_len=len(data);
            data = base64.b64encode(data);
            output.write("%d|%d|B|%s\n" % (len(data), raw_len, name));
            output.write(data);
            output.write("\n");  # separation

    file.close();

elif sys.argv[1]=='d':
    
    print_msg( "DECODE is called");

    fp = tempfile.TemporaryFile();

    file=zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED);
    
    while True:
        meta = inputt.readline();
        if not meta:
            break;

        (data_len, raw_len, mode, name) =[t(s) for t,s in zip((int,int,str,str),meta.split('|'))]; 
        if mode=='A':
            file.writestr(name.rstrip(), inputt.read(data_len));
            inputt.read(1); #skip last '\n'
        elif mode=='B':
            file.writestr(name.rstrip(), base64.b64decode(inputt.read(data_len)));
            inputt.read(1);
        else:
            # something is extremely wrong here.
            file.close();
            fp.close();
            sys.exit(1);
    
    # flush all write 
    file.close();

    fp.seek(0); 

    output.write(fp.read());


fp.close();    

#EOF

