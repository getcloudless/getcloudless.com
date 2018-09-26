#!/bin/bash

set -euo pipefail

MODULES_DATA="https://raw.githubusercontent.com/getcloudless/module_directory/master/modules.yml"

cat <<EOF
Script to update the latest module data.  Need this because github pages doesn't
support the kinds of plugins we'd need to do this in Jekyll itself.  This script
will copy data from $MODULES_DATA, and copy into "_data/modules.yml" in this
project.  You then have to commit and push to update this file.
EOF

cd "$(git rev-parse --show-toplevel)"

curl "https://raw.githubusercontent.com/getcloudless/module_directory/master/modules.yml" --output "_data/modules.yml"
