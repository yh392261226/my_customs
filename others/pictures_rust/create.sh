#!/usr/bin/env bash
MYRUNTIME=$(cat $HOME/.myruntime)
SCRIPTDIR=$MYRUNTIME/customs/others/pictures_rust

cd $SCRIPTDIR
cargo build --release

if [ -f $SCRIPTDIR/target/release/pictures ]; then
	cp $SCRIPTDIR/target/release/pictures $MYRUNTIME/customs/bin/rs_pictures
fi
