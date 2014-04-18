#/bin/sh

python zip_filter.py e <winword.docx >winword.plain
python zip_filter.py d <winword.plain >winword_new.docx


mkdir tmp/winword
mkdir tmp/winword_new

rm -rf winword
rm -rf winword_new

unzip -q winword.docx -d tmp/winword
unzip -q winword_new.docx -d tmp/winword_new

diff -rq tmp/winword tmp/winword_new


