JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-17.0.1.jdk/Contents/Home 
JAVAHOME=$JAVA_HOME
CLASS_PATH="$JAVA_HOME/lib"
CLASSPATH="$JAVA_HOME/lib"
PATH="$JAVA_HOME/bin:$PATH"
if [ "$PLATFORM" = 'Darwin' ]; then
    # Desc: function j 设置环境变量JAVA_HOME
    function j() { # Desc: function: j:设置JAVA_HOME的环境变量
        export JAVA_HOME=$(/usr/libexec/java_home -v1.$1);
    }
fi
