if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: 设置环境变量JAVA_HOME
    function j() { export JAVA_HOME=$(/usr/libexec/java_home -v1.$1); }
fi