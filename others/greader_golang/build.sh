MYRUNTIME=$(cat $HOME/.myruntime)
rm -f go.mod go.sum
go mod init greader
go mod tidy
go build -o greader main.go
mv greader $MYRUNTIME/customs/bin/greader
