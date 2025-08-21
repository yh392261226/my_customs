MYRUNTIME=$(cat $HOME/.myruntime)
rm -f go.mod go.sum
go mod init greader2
go mod tidy
go build -o greader2
mv greader2 $MYRUNTIME/customs/bin/greader2
