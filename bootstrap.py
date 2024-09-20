#!/usr/bin/python3
import argparse

from src.dotnet8.bootstrapper import Dotnet8Bootstrapper
from src.dotnet9.bootstrapper import Dotnet9Bootstrapper

def main():
    parser = argparse.ArgumentParser(description="The .NET Bootstrap Tool")

    # Expected arguments
    parser.add_argument('--version', type=str, help=".NET version to bootstrap per the VMR repo git tag", required=True)
    parser.add_argument('--arch', type=str, help="The architecture on which to bootstrap .NET",
                        choices=['amd64', 'arm64', 's390x', 'ppc64le'], default='amd64')

    parser.add_argument('--working-dir', type=str, help="Working directory", default=None)

    # Parse the command line arguments
    args = parser.parse_args()

    print("Welcome to the .NET Bootstrap Tool!")
    print("-----------------------------------")
    print("The tool will bootstrap .NET with the following configuration:")
    print(f".NET Version: {args.version}")
    print(f"Architecture: {args.arch}")
    print("-----------------------------------")

    if args.version[0] == '8':
        bootstrapper = Dotnet8Bootstrapper(args.version, args.arch, args.working_dir)
        bootstrapper.prepare()
        bootstrapper.build()
    elif args.version[0] == '9':
        bootstrapper = Dotnet9Bootstrapper(args.version, args.arch, args.working_dir)
        bootstrapper.prepare()
        bootstrapper.build()

if __name__ == "__main__":
    main()
