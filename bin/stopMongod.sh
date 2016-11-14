#!/bin/bash
ps -ef| grep 'mongod' | grep -v 'grep' | awk '{print $2}' | xargs kill -9
