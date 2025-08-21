MYRUNTIME=$(cat $HOME/.myruntime)
rm -f go.mod go.sum
go mod init reader
go mod tidy
go build -o reader
mv reader $MYRUNTIME/customs/bin/reader
