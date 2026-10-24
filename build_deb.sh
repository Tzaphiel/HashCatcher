#!/bin/bash
set -euo pipefail

rm -rf package
mkdir -p package/DEBIAN
mkdir -p package/usr/local/bin
mkdir -p package/usr/share/applications
mkdir -p package/usr/share/icons/hicolor/256x256/apps

cp dist/HashCatcher package/usr/local/bin/hashcatcher
chmod +x package/usr/local/bin/hashcatcher

cp assets/hashcather-logo.png \
   package/usr/share/icons/hicolor/256x256/apps/hashcatcher.png

cat > package/DEBIAN/control <<EOF
Package: hashcatcher
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Tahsasiyahu
Depends: python3, hcxtools, hashcat
Description: Offline wireless capture conversion utility for Hashcat workflows
EOF

cat > package/usr/share/applications/hashcatcher.desktop <<EOF
[Desktop Entry]
Name=HashCatcher
Exec=hashcatcher
Icon=hashcatcher
Type=Application
Categories=Utility;Security;
Terminal=false
EOF

dpkg-deb --build package

mv package.deb HashCatcher_1.0.0_amd64.deb
