#!/usr/bin/python3

from src.dotnet8.bootstrapper import Dotnet8Bootstrapper
import argparse

def main():
    parser = argparse.ArgumentParser(description="The .NET Bootstrap Tool")

    # Expected arguments
    parser.add_argument('--runtime', type=str, help="Runtime version to bootstrap", required=True)
    parser.add_argument('--sdk', type=str, help="SDK version to bootstrap", required=True)
    parser.add_argument('--arch', type=str, help="The architecture on which to bootstrap .NET",
                        choices=['amd64', 'arm64', 's390x', 'ppc64le'], default='amd64')
    
    parser.add_argument('--working-dir', type=str, help="Working directory", default=None)

    # Parse the command line arguments
    args = parser.parse_args()

    print("Welcome to the .NET Bootstrap Tool!")
    print("-----------------------------------")
    print("The tool will bootstrap .NET with the following configuration:")
    print(f"Runtime: {args.runtime}")
    print(f"SDK: {args.sdk}")
    print(f"Architecture: {args.arch}")
    print("-----------------------------------")

    if args.runtime[0] == '8':
        bootstrapper = Dotnet8Bootstrapper(args.runtime, args.sdk, args.arch, args.working_dir)
        bootstrapper.prepare()
        bootstrapper.build()

if __name__ == "__main__":
    main()
