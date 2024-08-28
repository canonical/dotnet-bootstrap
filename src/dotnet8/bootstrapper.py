import glob
import os
from pathlib import Path
import requests
import subprocess
import tarfile
import tempfile

from src.utils.dotnet import version_build_id
from src.utils.files import copy_files, replace_in_file
from src.utils.patches import apply_patch, extract_file_path_from_patch
from src.utils.xml import get_xml_tag_content


class Dotnet8Bootstrapper:

    def __init__(self,
                 runtime_version: str,
                 sdk_version: str,
                 arch: str,
                 working_directory: str | None):
        self.RuntimeVersion = runtime_version
        self.SdkVersion = sdk_version
        self.Arch = arch
        if working_directory is None:
            self.WorkingDirectory = tempfile.mkdtemp()
        else:
            working_directory_abs_path = os.path.abspath(working_directory)
            if not os.path.exists(working_directory_abs_path):
                os.mkdir(working_directory_abs_path)
            self.WorkingDirectory = working_directory_abs_path

    def prepare(self):
        print(f"Working out of {self.WorkingDirectory}")

        self.PackagesDir = os.path.join(self.WorkingDirectory, "local-packages")
        self.DownloadsDir = os.path.join(self.WorkingDirectory, "local-downloads")
        self.OutputDir = os.path.join(self.WorkingDirectory, "output")

        if not os.path.exists(self.PackagesDir):
            os.mkdir(self.PackagesDir)
        if not os.path.exists(self.DownloadsDir):
            os.mkdir(self.DownloadsDir)
        if not os.path.exists(self.OutputDir):
            os.mkdir(self.OutputDir)

        self._install_required_packages()
        self._install_nodejs()
        self._clone_repositories()

    def build(self):
        # runtime
        self._build_runtime()

        # sdk
        self._build_sdk()

        # aspnetcore
        self._patch_aspnetcore()
        self._build_aspnetcore()

        # installer
        self._patch_installer()
        self._build_installer()

    # ----------------------------------------------
    #              PREPARATION STAGE               |
    # ----------------------------------------------
    def _install_required_packages(self) -> None:
        print("-----------------------------------")
        print("Installing required packages")
        print("-----------------------------------")

        packages = [
            "build-essential",
            "gettext",
            "locales",
            "cmake",
            "llvm",
            "clang",
            "lldb",
            "liblldb-dev",
            "libunwind-dev",
            "libicu-dev",
            "liblttng-ust-dev",
            "libssl-dev",
            "libkrb5-dev",
            "zlib1g-dev"
        ]

        if self.Arch != "amd64":
            packages.extend([
                "qemu",
                "qemu-user-static",
                "binfmt-support",
                "debootstrap"
            ])

            if self.Arch == "s390x":
                packages.append("binutils-s390x-linux-gnu")
            elif self.Arch == "ppc64le":
                packages.append("binutils-powerpc64le-linux-gnu")
            elif self.Arch == "arm64":
                packages.append("binutils-aarch64-linux-gnu")

        subprocess.run(["apt", "update"])
        subprocess.run(["apt", "upgrade", "-y"])
        subprocess.run(["apt", "install", "-y"] + packages)

    def _install_nodejs(self) -> None:
        print("-----------------------------------")
        print("Installing Node.js")
        print("-----------------------------------")

        destination_directory = os.path.join(self.WorkingDirectory, "node")
        if os.path.exists(destination_directory):
            print(f"Node.js directory already exists at {destination_directory}")
            print("If this directory is incomplete or wrong, please remove it and run this script again.")
            return
        
        print("Downloading Node.js...")

        download_url = "https://nodejs.org/dist/v18.20.4/node-v18.20.4-linux-x64.tar.xz"
        response = requests.get(download_url)
        destination_file = os.path.join(self.WorkingDirectory, "node.tar.gz")

        if response.status_code == 200:
            with open(destination_file, 'wb') as file:
                file.write(response.content)
            print("Node.JS installed successfully!")
        else:
            print("Could not download Node.js")
            exit(-1)

        print("Extracting Node.js...")
        with tarfile.open(destination_file, "r:xz") as tar:
            tar.extractall(path=self.WorkingDirectory)

        os.remove(destination_file)

        # Rename the directory to a friendly name
        for node_dir in glob.glob(os.path.join(self.WorkingDirectory, "node-v*-linux-x64")):
            if os.path.isdir(node_dir):
                new_dir = os.path.join(self.WorkingDirectory, "node")
                os.rename(node_dir, new_dir)

        print(f"Extracted Node.js to {self.WorkingDirectory}")

    def _clone_repositories(self) -> None:
        repos = [
            {
                "url": "https://github.com/dotnet/runtime",
                "tag": "v" + str(self.RuntimeVersion)
            },
            {
                "url": "https://github.com/dotnet/sdk",
                "tag": "v" + str(self.SdkVersion)
            },
            {
                "url": "https://github.com/dotnet/aspnetcore",
                "tag": "v" + str(self.RuntimeVersion)
            },
            {
                "url": "https://github.com/dotnet/installer",
                "tag": "v" + str(self.SdkVersion)
            }
        ]

        print("-----------------------------------")
        print("Cloning repositories")
        print("-----------------------------------")

        for repo in repos:
            repo_name = repo["url"].split('/')[-1]
            if not os.path.exists(self.WorkingDirectory + "/" + repo_name):
                subprocess.run(["git", "clone", repo["url"]], cwd=self.WorkingDirectory)
            subprocess.run(["git", "checkout", repo["tag"]], cwd=os.path.join(self.WorkingDirectory, repo_name))
            subprocess.run(["git", "submodule", "init"], cwd=os.path.join(self.WorkingDirectory, repo_name))
            subprocess.run(["git", "submodule", "update"], cwd=os.path.join(self.WorkingDirectory, repo_name))

    # ----------------------------------------------
    #                 BUILD STAGE                  |
    # ----------------------------------------------
    def _build_runtime(self) -> None:
        configuration = "Release"
        runtime_version = get_xml_tag_content(
            os.path.join(self.WorkingDirectory, "aspnetcore", "eng", "Versions.props"),
            "MicrosoftNETCorePlatformsVersion")

        official_build_id = version_build_id(runtime_version)
        build_command = ["./build.sh", "--ci", "-c", configuration, "-arch", self.Arch, "-cross",
                        "-clang", f"/p:OfficialBuildId={official_build_id}"]

        print("-----------------------------------")
        print("Building runtime")
        print(f"Configuration = {configuration}")
        print(f"Version = {runtime_version}")
        print(f"Build command = {' '.join(build_command)}")
        print("-----------------------------------")

        if runtime_version is None:
            raise ValueError("Could not retrieve runtime version from Versions.props file")

        runtime_downloads_dir = os.path.join(self.DownloadsDir, "Runtime", runtime_version)
        os.makedirs(runtime_downloads_dir, exist_ok=True)

        rootfs = "/"
        if self.Arch != "amd64":
            print(f"Arch is {self.Arch}, needs to build crossrootfs")
            rootfs = os.path.abspath(os.path.join(self.WorkingDirectory, "runtime", ".tools/rootfs/" + self.Arch))
            print(f"Using rootfs = {rootfs}")
            if not os.path.exists(rootfs):
                subprocess.run(["./eng/common/cross/build-rootfs.sh", self.Arch, "bionic"],
                               cwd=os.path.join(self.WorkingDirectory, "runtime"), check=True)
            else:
                print(f"Crossrootfs directory found at {rootfs}")

        # Create a copy of the current environment and add/modify the variable
        env = os.environ.copy()
        env['ROOTFS_DIR'] = rootfs

        subprocess.run(build_command, env=env, cwd=os.path.join(self.WorkingDirectory, "runtime"), check=True)
        
        # Define the source directory and file patterns
        source_dir = f'{self.WorkingDirectory}/runtime/artifacts/packages/{configuration}'

        # Define the file patterns to copy
        patterns = [
            # PackagesDir
            f'{source_dir}/Shipping/Microsoft.NETCore.App.Host.linux-{self.Arch}.*.nupkg',
            f'{source_dir}/Shipping/Microsoft.NETCore.App.Runtime.linux-{self.Arch}.*.nupkg',
            # OutputDir
            f'{source_dir}/Shipping/dotnet-runtime-*-linux-{self.Arch}.tar.gz',
            f'{source_dir}/Shipping/runtime.linux-{self.Arch}.Microsoft.NETCore.DotNetHost.*.nupkg',
            f'{source_dir}/Shipping/runtime.linux-{self.Arch}.Microsoft.NETCore.DotNetHostPolicy.*.nupkg',
            f'{source_dir}/Shipping/runtime.linux-{self.Arch}.Microsoft.NETCore.DotNetHostResolver.*.nupkg',
            f'{source_dir}/NonShipping/runtime.linux-{self.Arch}.Microsoft.NETCore.ILAsm.*.nupkg',
            f'{source_dir}/NonShipping/runtime.linux-{self.Arch}.Microsoft.NETCore.ILDAsm.*.nupkg'
        ]

        # Copy files to PACKAGESDIR
        for pattern in patterns[:2]:
            copy_files(pattern, self.PackagesDir)

        # Copy files to DOWNLOADDIR
        download_pattern = f'{source_dir}/Shipping/dotnet-runtime-*-linux-{self.Arch}.tar.gz'
        copy_files(download_pattern, self.DownloadsDir + f'/Runtime/{runtime_version}')

        # Copy files to OUTPUTDIR
        for pattern in patterns[2:]:
            copy_files(pattern, self.OutputDir)

        print("Files copied successfully.")

    def _build_sdk(self) -> None:
        configuration = "Release"
        sdk_version = get_xml_tag_content(
            os.path.join(self.WorkingDirectory, "installer", "eng", "Versions.props"),
            "MicrosoftNETSdkPackageVersion")
        
        official_build_id = version_build_id(sdk_version)
        build_command = ["./build.sh", "--pack", "--ci", "-c", configuration, f"/p:Architecture={self.Arch}",
                         f"/p:OfficialBuildId={official_build_id}"]

        print("-----------------------------------")
        print("Building SDK")
        print(f"Configuration = {configuration}")
        print(f"Version = {sdk_version}")
        print(f"Build command = {' '.join(build_command)}")
        print("-----------------------------------")

        if sdk_version is None:
            raise ValueError("Could not retrieve runtime version from Versions.props file")

        sdk_downloads_dir = os.path.join(self.DownloadsDir, "Sdk", sdk_version)
        os.makedirs(sdk_downloads_dir, exist_ok=True)

        subprocess.run(build_command, cwd=os.path.join(self.WorkingDirectory, "sdk"), check=True)
        
        # Define the source directory and file patterns
        source_dir = f'{self.WorkingDirectory}/sdk/artifacts/packages/{configuration}'

        # Define the file patterns to copy
        patterns = [
            # DownloadsDir
            f'{source_dir}/NonShipping/dotnet-toolset-internal-*.zip',
            # PackagesDir
            f'{source_dir}/Shipping/Microsoft.DotNet.Common.*.nupkg'
        ]

        # Copy files to DOWNLOADDIR
        copy_files(patterns[0], self.DownloadsDir + f'/Sdk/{sdk_version}')

        # Copy files to PACKAGESDIR
        copy_files(patterns[1], self.PackagesDir)

        print("Files copied successfully.")

    def _patch_aspnetcore(self) -> None:
        print("-----------------------------------")
        print("Patching aspnetcore")
        print("-----------------------------------")

        patched_flag_file = Path(os.path.join(self.WorkingDirectory, "aspnetcore", "bootstrap-patched"))
        if (patched_flag_file.exists()):
            print("aspnetcore has already been patched. Skipping...")
            return

        for patch in glob.glob("src/dotnet8/patches/aspnetcore-*.patch"):
            print(f"Applying {patch}")
            # Replace @@DOWNLOADS_DIR_PATH@@
            patch_path = os.path.abspath(patch)
            updated_content = replace_in_file(
                patch_path, "@@DOWNLOADS_DIR_PATH@@", os.path.abspath(self.DownloadsDir))
            file_path = extract_file_path_from_patch(updated_content)
            apply_patch(updated_content, os.path.join(self.WorkingDirectory, "aspnetcore", file_path))

        patched_flag_file.touch()

    def _build_aspnetcore(self) -> None:
        configuration = "Release"
        aspnetcore_version = get_xml_tag_content(
            os.path.join(self.WorkingDirectory, "installer", "eng", "Versions.props"),
            "MicrosoftAspNetCoreAppRefInternalPackageVersion")

        official_build_id = version_build_id(aspnetcore_version)
        build_command = ["./eng/build.sh", "--pack", "--ci", "-c", configuration, "-arch", self.Arch,
                         f"/p:OfficialBuildId={official_build_id}"]
        
        # Create a copy of the current environment and add/modify the variable
        env = os.environ.copy()
        env['PATH'] = env['PATH'] + f":{self.WorkingDirectory}/node/bin"

        node_result = subprocess.run(["node", "--version"], env=env, capture_output=True, text=True, check=True)
        if node_result.returncode != 0:
            print("Could not execute node --version")
            print(node_result.stdout)
            print(node_result.stderr)
            exit(-1)

        print("-----------------------------------")
        print("Building aspnetcore")
        print(f"Configuration = {configuration}")
        print(f"Version = {aspnetcore_version}")
        print(f"Build command = {' '.join(build_command)}")
        print(f"Node version = {node_result.stdout.strip()}")
        print("-----------------------------------")

        if aspnetcore_version is None:
            raise ValueError("Could not retrieve ASP.NET Core runtime version from Versions.props file")

        aspnetcore_downloads_dir = os.path.join(self.DownloadsDir, "aspnetcore", "Runtime", aspnetcore_version)
        os.makedirs(aspnetcore_downloads_dir, exist_ok=True)

        subprocess.run(build_command, cwd=os.path.join(self.WorkingDirectory, "aspnetcore"), env=env)
        
        # Define the source directory and file patterns
        source_dir = f'{self.WorkingDirectory}/aspnetcore/artifacts'

        # Define the file patterns to copy
        patterns = [
            # PackagesDir
            f'{source_dir}/packages/{configuration}/Shipping/Microsoft.AspNetCore.App.Runtime.linux-{self.Arch}.*.nupkg',
            f'{source_dir}/packages/{configuration}/Shipping/Microsoft.DotNet.Web.*.nupkg',
            # DownloadsDir
            f'{source_dir}/installers/Release/aspnetcore-runtime-*-linux-{self.Arch}.tar.gz',
            f'{source_dir}/installers/{configuration}/aspnetcore-runtime-internal-*-linux-{self.Arch}.tar.gz',
            f'{source_dir}/installers/{configuration}/aspnetcore_base_runtime.version',
            # OutputDir
            f'{source_dir}/packages/{configuration}/Shipping/Microsoft.AspNetCore.App.Runtime.linux-{self.Arch}.*.nupkg'
        ]

        # Copy files to PACKAGESDIR
        for pattern in patterns[:2]:
            copy_files(pattern, self.PackagesDir)

        # Copy files to DOWNLOADDIR
        for pattern in patterns[2:5]:
            copy_files(pattern, self.DownloadsDir + f'/aspnetcore/Runtime/{aspnetcore_version}')

        # Copy files to OUTPUTDIR
        for pattern in patterns[5:]:
            copy_files(pattern, self.OutputDir)

        print("Files copied successfully.")

    def _patch_installer(self) -> None:
        print("-----------------------------------")
        print("Patching installer")
        print("-----------------------------------")

        patched_flag_file = Path(os.path.join(self.WorkingDirectory, "installer", "bootstrap-patched"))
        if (patched_flag_file.exists()):
            print("installer has already been patched. Skipping...")
            return

        for patch in glob.glob("src/dotnet8/patches/installer-*.patch"):
            print(f"Applying {patch}")
            # Replace @@PACKAGES_DIR_PATH@@
            patch_path = os.path.abspath(patch)
            updated_content = replace_in_file(
                patch_path, "@@PACKAGES_DIR_PATH@@", os.path.abspath(self.PackagesDir))
            file_path = extract_file_path_from_patch(updated_content)
            apply_patch(updated_content, os.path.join(self.WorkingDirectory, "installer", file_path))

        patched_flag_file.touch()

    def _build_installer(self) -> None:
        configuration = "Release"
        installer_version = str(self.RuntimeVersion)

        official_build_id = version_build_id(installer_version)
        build_command = ["./build.sh", "--ci", "-c", configuration, "-a", self.Arch,
                         f"/p:OfficialBuildId={official_build_id}", "/p:HostRid=linux-x64",
                         f"/p:PublicBaseURL=file://{self.DownloadsDir}/"]

        print("-----------------------------------")
        print("Building installer")
        print(f"Configuration = {configuration}")
        print(f"Version = {installer_version}")
        print(f"Build command = {' '.join(build_command)}")
        print("-----------------------------------")

        subprocess.run(build_command, cwd=os.path.join(self.WorkingDirectory, "installer"), check=True)

        # Define the source directory and file patterns
        source_dir = f'{self.WorkingDirectory}/installer/artifacts/packages/{configuration}'

        copy_files(f"{source_dir}/Shipping/dotnet-sdk-*-linux-{self.Arch}.tar.gz", self.OutputDir)

        print("Files copied successfully.")
