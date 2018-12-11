#!/bin/bash

SERVICE_NAME="web-$(git rev-parse --short HEAD)"
python example-static-site/helpers/deploy.py cloudless consul-1 "$SERVICE_NAME" \
    getcloudless.com https://github.com/getcloudless/getcloudless.com/ "Cloudless"
