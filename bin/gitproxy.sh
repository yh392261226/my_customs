#!/bin/bash
ADDRESS=127.0.0.1
PORT=1080
export http_proxy=$ADDRESS:$PORT
export https_proxy=$http_proxy
