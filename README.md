# Zippey: A Git filter for friendly handling of ZIP-based files

## Motivation

There are many types of ZIP-based files that contain plain text content,
such as:

* Microsoft Office
  (`.docx`, `.xlsx`, `.pptx`)
* OpenOffice
  (`.odt`)
* Java Archive
  (`.jar`)
* FreeCAD
  (`.fcstd`)

They can not efficiently be tracked by git,
since the compression smears what parts have been modified
and what parts remain the same across commits.
This saves the archived text files as a new binary blob,
every time the file is modified,
which prevents Git from versioning these files in a meaningful way.

## Method

Zippey is a Git filter that unzips zip-based files
into a simple text format during `git add`/`git commit` ("clean" process)
and recover the original zip-based file after `git checkout` ("smudge" process).

## Benefits

1. Since the diff is taken on the "clean" file,
it is likely that the real changes to the file can be reflected in a meaningful way
by the built-in `git diff` command.
This solves the problem of diffs for these files
normally being useless and unreadable for humans.
2. The second benefit, is that the repository might end up much smaller in disc-size.
Imagine you have one huge zip archive (~100MB), and over a series of 10 commits,
you change only a small portion of one text file contained in this archive.
Traditionally, the archive data might likely change completely in each commit,
and thus your repo size would grow by 10 * 100MB.
With this filter though, the repo will only grow by the size of the actual changes
in the text file, which might sum up to only 1KB.

## File Format

The text format is defined as a series of records, where each record represents
a file in the original zip-based file. A record is composed of two parts, a
header that contains the meta information and a body that contains the content.
The header is a few data fields, separated by the pipe character, like this:

    length|raw-length|type|filename

where:

* `length` is an ASCII-coded integer,
  denoting the length in bytes of the following data section
* `raw-length` is the original length of the data
  (before transformation took place)
* `type` is A for text data and B for binary data
* `filename` is the original file name
  (including the path, if the zipped file contains directories)

Immediately after the header, there is a line feed (LF => `'\n'`),
followed by `length` bytes of data,
another LF and then the next record,
and so on:

    [header1]\n[data1]\n[header2]\n[data2] ...

There are two types of data sections:

1. If the file contains only text data,
   its content is copied to the data section without any change
2. Otherwise, data is base64-coded,
   to ensure the entire file is in text format.

## How to use

### Setup

Before your first use of this filter,
you need to set it up.

Make sure that you have Python installed in your system,
and that the `python` command is available through your `PATH` env variable under Windows.

Then you need to install this filter with Git.

For this, clone the repository and change into it:

    git clone git@bitbucket.org:sippey/zippey.git
    cd zippey

Then, we add the filters,

on Unix/Linux/BSD/OSX:

    # smudge filter
    git config --global --replace-all filter.zippey.smudge "$PWD/zippey.py d"
    # clean filter
    git config --global --replace-all filter.zippey.clean  "$PWD/zippey.py e"

on Windows:

    # smudge filter
    git config --global --replace-all filter.zippey.smudge "python %cd%/zippey.py d"
    # clean filter
    git config --global --replace-all filter.zippey.clean  "python %cd%/zippey.py e"

### Use

Now we still need to enable the filter,
which is best done by adding a `.gitattributes` file to each repository
in which you want to use this filter.

Here sample content of a `.gitattributes` file
that enforces Microsoft Word files to use this filter:

    *.docx filter=zippey

## Side-effects

In the repository, the file is _not_ saved as an archive,
but as an uncompressed,
text-based representation of the content and meta information.
There are two circumstances under which this might be a problem:

1. If you download a file handled by this filter
  directly from an online repository website -
  for example through the GitHub web interface -
  it will still be in the text format.
  This also applies if you download the whole repo content
  as an archive.
2. If you have a local repository,
  but you do not have this filter setup,
  you also end up with the file in text format.

__Workaround:__ If it is just a single file, you can recover it by:

        python zippey.py d < downloaded-text-file > recovered-zip-based-file

