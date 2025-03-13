#!/bin/bash

# This script will create a build for a python project.
# Example: The script expects the project with the following structure -
#       data
#       projectx
#           config.yaml
#           main.py
#       build.sh
#       README.md
#       requirements.txt
#
# Usage: ./build.sh projectx
#
# Output: A zip file is generated which has the following structure when unzipped -
#       bin
#           run-projectx
#       conf
#           config.yaml
#       data
#       README.md


clean() {
  PROJECT=$1
  BUILD_DIR="build"
  DIST_DIR="dist"

  if [ -f "$PROJECT".zip ]; then
    rm "$PROJECT".zip
  fi

  if [ -d "$PROJECT" ]; then
    rm -rf "$PROJECT"
  fi

  if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
  fi

  if [ -d "$DIST_DIR" ]; then
    rm -rf "$DIST_DIR"
  fi
}

build() {
  PROJECT=$1
  EXECUTABLE="run-$PROJECT"
  
  echo "Cleaning..."
  clean "$PROJECT"
  
  echo "Building $PROJECT..."
  if [ ! -d "venv" ]; then
    echo "Creating virtual environment.."
    python3 -m venv "venv"
    source venv/bin/activate
    pip3 install -r requirements.txt
  fi

  pyinstaller "$PROJECT"/main.py --onefile --noconfirm --name "$EXECUTABLE" --specpath dist
  cp dist/"$EXECUTABLE" "$PROJECT"/bin/

  mkdir "$PROJECT"/data
  mkdir "$PROJECT"/conf

  cp data/* "$PROJECT"/data/
  cp projectx/config.yaml "$PROJECT"/conf/
  cp README.md "$PROJECT"/

  rm -r build dist
  zip -r "$PROJECT".zip "$PROJECT"
  rm -rf "$PROJECT"

  echo "Build completed!"
}

if [ "$#" -eq 1 ]; then
  build $1
else
  echo "The script expects an argument. Exiting.."
  exit 1
fi
