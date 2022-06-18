#!/usr/bin/env python
#
#  Copyright (c) 2019, Sippey Fun Lab <sippey@gmail.com>
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Sippey
# Fun Lab BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# This is the BSD 3-clause "New" or "Revised" license (bsd-3-clause).
#

#
# Zippey is a Git filter for friendly handling of ZIP-based files.
# These are the unit tests for it.
# See the README for further details.
#

import unittest
import zipfile
import tempfile
import os
import io
import filecmp
import shutil
import zippey


def create_temp_dir():
    return tempfile.mkdtemp(prefix="test_zippey_")


def create_zip_file(file_path, file_list):
    with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zfp:
        for cont_file in file_list:
            zfp.write(cont_file.rstrip(), cont_file)


def unzip(zip_file_path, dst_dir):
    with zipfile.ZipFile(zip_file_path, 'r') as zfp:
        zfp.extractall(dst_dir)


class TestZippey(unittest.TestCase):

    content = ["zippey.py",  "test_zippey.py",  "README.md"]

    def test_encode_decode_content_comparison_with_original(self):
        try:
            temp_dir = create_temp_dir()
            file_orig = os.path.join(temp_dir, "orig.zip")
            file_encoded = os.path.join(temp_dir, "encoded.txt")
            file_decoded = os.path.join(temp_dir, "decoded.zip")
            dir_unzipped = os.path.join(temp_dir, "unzipped")

            # Create a simple ZIP file containing this repos text files
            create_zip_file(file_orig, self.content)

            # Encode the ZIP file into a text format
            with io.open(file_orig, 'rb') as zip_file:
                with open(file_encoded, 'wb') as text_file:
                    zippey.encode(zip_file, text_file)

            # Check if file content appears in the encoded format.
            # This is important to be bale to see changes
            # in archived files in the git history.
            for cont_file in self.content:
                msg = (f"Can not find file contents of '{cont_file}'"
                       f"in encoded archive!")
                with open(cont_file) as orig_file:
                    with open(file_encoded) as encoded_file:
                        self.assertTrue(orig_file.read() in encoded_file.read(), msg)

            # Decode back into a ZIP file
            with io.open(file_encoded, 'rb') as text_file:
                with open(file_decoded, 'wb') as zip_file:
                    zippey.decode(text_file, zip_file)

            # Unzip our re-decoded ZIP file
            os.mkdir(dir_unzipped)
            unzip(file_decoded,  dir_unzipped)

            # Compare the re-decoded ZIP contents with the original text files
            for cont_file in self.content:
                self.assertTrue(
                        filecmp.cmp(
                                os.path.join(dir_unzipped, cont_file),
                                cont_file,
                                shallow = False),
                        "File contents of '{0}' differ!".format(cont_file))
        finally:
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    unittest.main()
