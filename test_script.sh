#/bin/sh

python zippey.py e < winword.docx > winword.plain
python zippey.py d < winword.plain > winword_new.docx

python zippey.py d < winword.docx > winword_prezipped.docx

cmp winword.docx winword_prezipped.docx || exit 1

[ -e "tmp" ] && rm -rf tmp
mkdir -p tmp/winword
mkdir -p tmp/winword_new

unzip -q winword.docx -d tmp/winword
unzip -q winword_new.docx -d tmp/winword_new

rm -rf winword.plain
rm -rf winword_new.docx
rm -rf winword_prezipped.docx

diff -rq tmp/winword tmp/winword_new


