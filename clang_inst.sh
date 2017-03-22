#!/bin/sh
 
SRCDIR="/opt/src"
INSTDIR="/opt/llvm"
 
echo ""
 
if [ -d $SRCDIR/llvm/.svn ] ; then
	echo "Updating "$SRCDIR"/llvm ..."
	svn up $SRCDIR/llvm $SRCDIR/llvm/tools/clang
else
	echo "Checking out "$SRCDIR"/llvm ..."
	svn checkout http://llvm.org/svn/llvm-project/llvm/trunk $SRCDIR/llvm
	svn checkout http://llvm.org/svn/llvm-project/cfe/trunk $SRCDIR/llvm/tools/clang
fi
 
 
rm -rf $INSTDIR
 
mkdir $SRCDIR/llvm_cmake
cd $SRCDIR/llvm_cmake
 
echo ""
echo "Building..."
 
cmake ../llvm \
	-DCMAKE_INSTALL_PREFIX:STRING=$INSTDIR \
	-DCMAKE_BUILD_TYPE:STRING=Debug \
	-DLLVM_ENABLE_THREADS:BOOL=ON
 
make -j6
 
echo ""
echo "Installing..."
 
make install
 
 
cp $SRCDIR/llvm/tools/clang/tools/scan-view/scan-view $INSTDIR/bin/
cp $SRCDIR/llvm/tools/clang/tools/scan-view/*.py $INSTDIR/bin/
 
cp $SRCDIR/llvm/tools/clang/tools/scan-build/scan-build $INSTDIR/bin/
cp $SRCDIR/llvm/tools/clang/tools/scan-build/ccc-analyzer $INSTDIR/bin/
cp $SRCDIR/llvm/tools/clang/tools/scan-build/c++-analyzer $INSTDIR/bin/
cp $SRCDIR/llvm/tools/clang/tools/scan-build/sorttable.js $INSTDIR/bin/
cp $SRCDIR/llvm/tools/clang/tools/scan-build/scanview.css $INSTDIR/bin/
 
echo ""
echo "Done!"



# post build
# export PATH=$PATH:/opt/llvm/bin
# cmake ../blender \
#	-DCMAKE_CXX_COMPILER:FILEPATH=/opt/clang/bin/c++-analyzer \
#	-DCMAKE_C_COMPILER:FILEPATH=/opt/clang/bin/ccc-analyzer
