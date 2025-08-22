MYRUNTIME=$(cat $HOME/.myruntime)
rm -f go.mod go.sum
go mod init ureader
go mod tidy
go build -o ureader
mv ureader $MYRUNTIME/customs/bin/ureader
