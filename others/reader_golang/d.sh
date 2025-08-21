#!/usr/bin/env bash

for file in $(ls ./*.go); do
    echo "" >> record.log
    echo $file >> record.log
    echo "\n=======================\n" >> record.log
    cat $file >> record.log
    echo "" >> record.log
done