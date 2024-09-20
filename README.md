# .NET Bootstrap Script

The .NET Bootstrap Script allows for the easy bootstrapping of .NET builds targeting the IBM Z and IBM Power Linux architectures.

## Supported .NET Versions

The script currently supports:

- .NET 8
- .NET 9

## How to Use

### Running the Script

> [!CAUTION]
> This script will install system-wide packages with `apt`, so make sure you run it from a disposable VM or container if you don't want these packages installed on your main system. You also need to run the script as root.

Run the script as follows:

```
$ sudo ./bootstrap.py --version <version> --arch <arch> --working-dir <dir>
```

Keep in mind that:

- You are meant to run this script on an `amd64` machine, even if you are targeting other architectures.
- Your `<version>` should equal one available as a [VMR](https://github.com/dotnet/dotnet) git tag without the "v" preffix, e.g. 8.0.8.
- Possible values for `--arch` are `amd64`, `arm64`, `s390x`, and `ppc64le`. This script has been thoroughly tested for `s390x` and `ppc64le` only.
- If you don't choose a working directory, the script will automatically create a temporary directory and place the build outputs there.

### Script outputs

Once the script finishes running, your working directory will contain the following content:

- The repositories that were utilized to build the bootstrap SDK, which are currently *runtime*, *sdk*, *aspnetcore*, and *installer*.
- A *local-downloads* directory used to provide NuGet packages for the build process in places where these are retrieved from a well-known URL (see [src/dotnet8/patches/aspnetcore-downloads-dir-source.patch](src/dotnet8/patches/aspnetcore-downloads-dir-source.patch)).
- A *local-packages* directory to serve as a NuGet source for the installer (see [src/dotnet8/patches/installer-local-repo-nuget-source.patch](src/dotnet8/patches/installer-local-repo-nuget-source.patch)).
- An *output* directory that contains the results of the bootstrap process, which are: a runtime, an SDK, and several architecture-specific NuGet packages used to build .NET.

### Building the VMR

Once you have all the products of the bootstrap process, you can use them to build the full [VMR](https://github.com/dotnet/dotnet).

To build version `N` of the VMR, you need to have bootstrapped version `N-1` of .NET using this script. As an example, these are the steps necessary to build the VMR for version 8.0.8 of .NET on s390x:

#### 1. Bootstrap .NET 8.0.7

```
$ sudo ./bootstrap.py --version 8.0.7 --arch s390x --working-dir $HOME
```

#### 2. Extract the SDK from the output directory

```
$ mkdir dotnet
$ tar xzf output/dotnet-sdk-8.0.107-linux-s390x.tar.gz -C dotnet
```

#### 3. Clone the VMR and checkout the right tag

```
$ git clone https://github.com/dotnet/dotnet dotnet-vmr
$ cd dotnet-vmr
$ git checkout v8.0.8
```

> [!NOTE]
> We are building version 8.0.8 of .NET, so you need to have bootstrapped version 8.0.7 using the script provided in this repo.

#### 4. Run the VMR prep script

We need to temporarily copy the dotnet directory to the root of the VMR as `.dotnet`, so that the prep script will identify that there is already a .NET SDK available and will use it for subsequent tasks.

You can safely delete the `.dotnet` directory once that process is done. If you build the VMR with the `.dotnet` directory (and don't specify another SDK with `--with-sdk`), the build errors out.

```
$ cp -RLp ../dotnet .dotnet
$ ./prep.sh --no-sdk
$ rm -rf .dotnet
```

#### 5. Copy the supporting arch-specific NuGet packages to the VMR

```
$ mkdir prereqs/packages/previously-source-built
$ cp ../output/*.nupkg prereqs/packages/previously-source-built
```

#### 6. Run the build script

Extra verbosity is useful for eventual debugging, so you can run the command as follows:

```
$ VERBOSE=1 ./build.sh --clean-while-building --with-sdk ../dotnet -- /v:n /p:SkipPortableRuntimeBuild=true /p:LogVerbosity=n /p:MinimalConsoleLogOutput=false /p:ContinueOnPrebuiltBaselineError=true
```

## Credits

This script was based on another script, which was provided by IBM, to bootstrap .NET 7 for Power. You can read the original blog post [here](https://community.ibm.com/community/user/powerdeveloper/blogs/sapana-khemkar/2023/01/13/cross-build-dotnet7-on-x86-ibm-power).
