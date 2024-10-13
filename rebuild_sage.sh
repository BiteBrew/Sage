#!/bin/bash
sudo dpkg -r sage
pyinstaller --noconfirm sage.spec
cp ./dist/sage/sage ./sage_deb_package/usr/local/bin/sage
cp -ra ./dist/sage/_internal ./sage_deb_package/usr/local/bin/_internal
sudo dpkg-deb --build sage_deb_package
sudo dpkg -i sage_deb_package.deb
