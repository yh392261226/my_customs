#!/usr/bin/env bash
RECLOG=record.log

echo "" > $RECLOG
echo "requirements.txt" >> $RECLOG
echo "----------------------------------------" >> $RECLOG
cat "requirements.txt" >> $RECLOG
echo "" >> $RECLOG
echo "" >> $RECLOG

for f in $(ls ./*.py); do
    echo "$f" >> $RECLOG
    echo "----------------------------------------" >> $RECLOG
    cat "$f" >> $RECLOG
    echo "" >> $RECLOG
    echo "" >> $RECLOG
done