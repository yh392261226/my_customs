#!/usr/bin/env bash
echo "" > record.log
for f in $(ls ./*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done

for f in $(ls ./config/*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done

for f in $(ls ./core/*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done

for f in $(ls ./tts/*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done

for f in $(ls ./ui/*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done

for f in $(ls ./utils/*.go); do
    echo "$f" >> record.log
    echo '------------------------' >> record.log
    cat "$f" >> record.log
    echo "" >> record.log
done