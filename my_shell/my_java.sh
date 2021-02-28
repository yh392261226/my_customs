JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_111.jdk/Contents/Home
CLASS_PATH="$JAVA_HOME/lib"
PATH="$JAVA_HOME/bin:$PATH"
if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: 设置环境变量JAVA_HOME
    function j() { export JAVA_HOME=$(/usr/libexec/java_home -v1.$1); }
fi
