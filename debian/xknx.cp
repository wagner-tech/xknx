#!/bin/bash
set -e

mkdir -p $1/usr/lib/python3/dist-packages/
rsync -av ./xknx/ $1/usr/lib/python3/dist-packages/xknx/

