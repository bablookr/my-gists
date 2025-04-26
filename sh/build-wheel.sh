#!/bin/bash

# This script creates a simple python project and demonstrates building
# of a wheel distribution and uploading it to PyPI.
#`
# Usage:
#
# Structure of Project:
#     simplemaths
#         __init__.py
#     build-wheel.sh
#     LICENSE
#     README.md
#     setup.py
#
# Build Output:
#     build
#     dist
#     simplemaths.egg-info
#
# As the script uses `twine` to upload the package to PyPI, it assumes the
# existence of .pypirc file with a valid API token.

PROJECT="simplemaths"
VERSION="0.1.0"
AUTHOR="Babloo Kumar"
YEAR=$(date +%Y)

clean() {
  if [ -d $PROJECT ]; then
    rm -rf $PROJECT build dist $PROJECT.egg-info
    rm setup.py README.md LICENSE
  fi

  echo "Uninstalling $PROJECT.."
  pip3 uninstall -y $PROJECT

  echo "Cleanup done!"
}

create_python_files() {
  echo "Creating Python files..."

  cat <<EOL >$PROJECT/__init__.py
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
EOL

  cat <<EOL >setup.py
from setuptools import setup, find_packages

setup(
    name="$PROJECT",
    version="$VERSION",
    author="$AUTHOR",
    long_description="<h1>$PROJECT</h1> An example Python project to build a wheel distribution and upload to PyPI",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[]
)
EOL
}

add_readme() {
  echo "<h1>$PROJECT</h1> An example Python project to build a wheel distribution and upload to PyPI" >README.md
}

add_license() {
  echo "Adding MIT License..."
  wget -q -O LICENSE https://raw.githubusercontent.com/github/choosealicense.com/refs/heads/gh-pages/_licenses/mit.txt
  sed -i '' "s/\[year\]/$YEAR/g" LICENSE
  sed -i '' "s/\[fullname\]/$AUTHOR/g" LICENSE
  sed -i '' '/^---$/,/^---$/d' LICENSE
}

build() {
  upload=$1

  echo "Cleaning..."
  clean

  echo "Building $PROJECT.."
  if [ ! -d "venv" ]; then
    echo "Creating virtual environment.."
    python3 -m venv "venv"
    source venv/bin/activate
    pip3 install setuptools
    pip3 list
  fi

  mkdir $PROJECT
  create_python_files
  add_readme
  add_license

  python setup.py sdist bdist_wheel --plat-name macosx_11_0_arm64

  if [ "$upload" == "true" ]; then
    upload_to_pypi
  fi

  echo "Build completed!"
}

upload_to_pypi() {
  echo "Uploading package to PyPI..."
  pip3 install twine
  twine upload dist/*
  echo "Done! Your package has been uploaded to PyPI."
}

install() {
  install_type=$1
  case $install_type in
  "remote")
    echo "Installing from PyPI..."
    pip3 install $PROJECT
    ;;
  "local")
    echo "Installing from local wheel..."
    pip3 install dist/${PROJECT}-${VERSION}-py3-none-macosx_11_0_arm64.whl
    ;;
  "editable")
    echo "Installing in editable mode..."
    pip3 install -e .
    ;;
  "none")
    echo "Skipping installation."
    ;;
  *)
    echo "Invalid value for --install. Use 'remote', 'local' or 'editable'. Exiting..."
    exit 1
    ;;
  esac
  pip3 list
}

if [ "$1" == "--upload" ]; then
  upload="$2"
  install_type="none"
  if [ "$3" == "--install" ]; then
    install_type="$4"
  fi

  if [[ "$upload" =~ ^(true|false)$ ]] && [[ "$install_type" =~ ^(remote|local|editable|none)$ ]]; then
    build "$upload"
    install "$install_type"
  else
    echo "Invalid parameters. Usage: $0 --upload <true|false> [--install <remote|local|editable>]"
    exit 1
  fi
else
  echo "Usage: $0 --upload <true|false> [--install <remote|local|editable>]"
  exit 1
fi
