# Zippey: A Git filter for friendly handling of ZIP-based files

## Intro

There are many types of ZIP-based files, such as  Microsoft Office .docx,
.xlsx, .pptx files, OpenOffice .odt files and jar files, that contains 
plain text content but that can't really be tracked by git since the
compression smears what parts have been modified and what parts remain the same
across commits. This prevent Git from versioning these files and it saves them
as a new binary blob every time the file is modified. 

## Method

Zippey is a Git filter that unzips zip-based files into a simple text format
during git add/commit ("clean" process) and recover the original zip-based 
file after git checkout ("smudge" process). Since diff is taken on the 
"clean" file, it is likely that the real changes to file can be reflected by
the built-in git diff command. This solves the problem of diffs for these files
normally being useless and unreadable for humans.

## File Format

The text format is defined as a series of records, where each record represents
a file in the original zip-based file. A record is composed of two parts, a
header that contains the meta information and a body that contains the data.
The header is a few data fields separated by the pipe character like this:

>    length|raw_length|type|filename

where length is an ascii coded integer of the length of the following data
section, raw_length is the original length of data (if transformation is
taken), type is A for text data and B for binary data, and filename is the
original file name (including path if the ziped file contains directories).
Immediately after the header, there is a line feed ('\n'), followed by "length"
bytes of data, and then another LF and then the next record and so on.

>   [header1]\n[data1]\n[header2]\n[data2] ...

There are two types of data section. If the file contains only text data, 
its content is copied to data section without any change, otherwise, data 
is base64 coded to ensure the entire file is in text format.

## Try Out

Before trying anything, please remember to add the file filter by running the
following commands inside the directory you have cloned.

First to add the smudge filter,

>   git config filter.zippey.smudge "$PWD/zippey.py d"

then the clean filter,

>   git config filter.zippey.clean  "$PWD/zippey.py e"

The .gitattributes file has settings that enforce Microsoft Word docx file to 
use this filter. The only side-effect for this is that, if you download a docx
file directly from an online repository host, the docx file will still be in
the text format. If it is just a single file you can use

>   zippey.py d < downloaded-file > recovered-file

to recover it.

