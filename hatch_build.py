# To resolve the "Import hatchling.builders.hooks.plugin.interface could not be resolved" error:
# pip install hatchling
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import os
import sys
import platform
import subprocess
import packaging.version as packaging_version
from typing import Any, Dict, List, Optional

# Add logging imports
import logging
import datetime
import tempfile
import traceback
import shutil

# Constants
BUILD_DIR = "dist"
BUILD_DIR_LOGS_DIR = "dist_logs"

# Configure logging
logger = logging.getLogger("conditional_method_build")
logger.setLevel(logging.DEBUG)
logger.handlers = []  # Clear existing handlers

# Log to file
log_file = os.path.join(
    BUILD_DIR_LOGS_DIR, 
    f"build_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

# Log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter('%(levelname)s: %(message)s')
)
logger.addHandler(console_handler)

DEFAULT_EXTRA_COMPILE_ARGS_LINUX = [
    "-Werror",
    "-Wall",
    "-Wextra",
    "-std=c99",
    "-O3",  # Maximum optimization
    "-march=native",  # Optimize for the host CPU
    "-mtune=native",  # Tune for the host CPU
    "-ffast-math",  # Allow aggressive floating-point optimizations
    "-funroll-loops",  # Unroll loops for better performance
    "-fomit-frame-pointer",  # Reduce stack overhead
    "-flto",  # Link-time optimization
    "-falign-functions=32",  # Better instruction alignment
    "-falign-jumps=32",  # Improve branch prediction
    "-falign-loops=32",  # Optimize loop execution
    "-fstrict-aliasing",  # Enable strict aliasing for better optimization
    "-fprefetch-loop-arrays",  # Prefetch data for loops
    "-ftree-vectorize",  # Enable auto-vectorization
    "-fipa-pta",  # Interprocedural pointer analysis
    "-fipa-cp-clone",  # Interprocedural constant propagation
    "-fprofile-generate",  # Profile-guided optimization (for training runs)
]

DEFAULT_EXTRA_COMPILE_ARGS_WINDOWS = [
    "/WX",
    "/W3",
    "/std:c11",
    "/O2",
    "/arch:AVX2",
    "/fp:fast",
    "/GL",  # Whole program optimization
    "/Gy",  # Enable function-level linking
    "/Qpar",  # Auto-parallelization
    "/Qvec",  # Auto-vectorization
    "/Qfast_transcendentals",  # Fast transcendental functions
    "/Qopt-report:5",  # Optimization report for debugging
    "/fp:except-",  # Disable floating-point exceptions
]


def _create_build_log_directory_if_not_exists():
    if not os.path.exists(BUILD_DIR_LOGS_DIR):
        os.makedirs(BUILD_DIR_LOGS_DIR)
    return BUILD_DIR_LOGS_DIR


class CustomBuildHook(BuildHookInterface):
    """
    A build hook for building the conditional_method C extension module.

    This hook handles the compilation of the C extension module with optimized
    compiler flags for different platforms.
    """

    EXTENSION_NAME = "_lib"
    SOURCE_FILE = "src/conditional_method/_lib.c"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Initialize the build hook with version information."""
        logger.info(f"Initializing CustomBuildHook with version: {version}")
        logger.debug(f"Build data: {build_data}")
        self.version = self.metadata.version
        self.build_data = build_data  # Store for later use, don't call build here
        self.build(directory=self.directory, artifacts=[])
        logger.info("CustomBuildHook initialized successfully")

    def clean(self, directory: str) -> None:
        """Clean any artifacts from the build directory."""
        logger.info(f"Cleaning directory: {directory}")
        # Nothing to clean specifically for this hook
        logger.debug("No specific cleaning actions taken")

    def build(self, directory: str, artifacts: List[str], **kwargs: Any) -> List[str]:
        """
        Build the C extension module.
        
        Args:
            directory: The directory where the build will be performed
            artifacts: A list of file artifacts
            **kwargs: Additional arguments
            
        Returns:
            A list of build artifacts
        """
        logger.info(f"Starting build in directory: {directory}")
        logger.debug(f"Artifacts: {artifacts}")
        logger.debug(f"Additional build arguments: {kwargs}")
        
        try:
            # Determine platform-specific compiler flags
            logger.info(f"Determining compiler flags for platform: {sys.platform}")
            extra_compile_args = []
            define_macros = [("PY_SSIZE_T_CLEAN", None), ("NDEBUG", None)]  # Add essential macros
            
            if sys.platform == "darwin":
                logger.info("Configuring for macOS platform")
                # macOS specific flags
                extra_compile_args = ["-O3", "-Wno-unused-result", "-Wno-unused-function"]
                if platform.machine() == "arm64":
                    logger.info("Detected Apple Silicon (arm64)")
                    extra_compile_args.append("-arch arm64")
                else:
                    logger.info(f"Detected Intel Mac ({platform.machine()})")
                    extra_compile_args.append("-arch x86_64")
                
            elif sys.platform == "win32":
                logger.info("Configuring for Windows platform")
                # Windows specific flags
                extra_compile_args = ["/O2", "/W3", "/Zc:inline", "/MD"]
                define_macros.append(("NDEBUG", None))
                
            else:
                logger.info(f"Configuring for UNIX-like platform: {sys.platform}")
                # Linux and other UNIX-like platforms
                extra_compile_args = ["-O3", "-Wno-unused-result", "-Wno-unused-function"]
            
            logger.debug(f"Selected compiler flags: {extra_compile_args}")
            logger.debug(f"Selected macros: {define_macros}")
            
            # Build the extension
            logger.info("Building C extension module")
            self._build_extension(
                directory,
                self.EXTENSION_NAME,
                self.SOURCE_FILE,
                extra_compile_args,
                define_macros
            )
            
            # Determine the filename of the built extension
            ext_suffix = self._get_extension_suffix()
            logger.info(f"Extension suffix determined as: {ext_suffix}")
            
            extension_path = os.path.join(
                directory, "conditional_method", f"{self.EXTENSION_NAME}{ext_suffix}"
            )
            logger.info(f"Built extension path: {extension_path}")
            
            # Check if the extension was built correctly
            if not os.path.exists(extension_path):
                error_msg = f"Extension not found at expected path: {extension_path}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Extension successfully built: {os.path.getsize(extension_path)} bytes")
            logger.debug(f"Extension timestamp: {datetime.datetime.fromtimestamp(os.path.getmtime(extension_path))}")
            
            # Return the compiled extension as an artifact
            # Convert to relative path for artifacts list
            rel_extension_path = os.path.relpath(extension_path, directory)
            logger.info(f"Adding artifact: {rel_extension_path}")
            
            # Remove the source file from artifacts if it's there
            source_rel_path = "conditional_method/_lib.c"
            if source_rel_path in artifacts:
                logger.info(f"Removing source file from artifacts: {source_rel_path}")
                artifacts.remove(source_rel_path)
            
            # Return the extension artifact
            return artifacts + [rel_extension_path]
            
        except Exception as e:
            logger.error(f"Build failed with error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _build_extension(
        self,
        directory: str,
        extension_name: str,
        source_file: str,
        extra_compile_args: List[str],
        define_macros: List[tuple],
    ) -> None:
        """
        Build the C extension using setup.py.

        Args:
            directory: The directory where the build will be performed
            extension_name: The name of the extension module
            source_file: The C source file path
            extra_compile_args: Additional compiler arguments
            define_macros: Preprocessor macro definitions
        """
        logger.info(
            f"Building extension '{extension_name}' from source '{source_file}'"
        )
        logger.debug(f"Build directory: {directory}")

        # Verify source file exists
        abs_source_path = os.path.abspath(source_file)
        if not os.path.exists(abs_source_path):
            error_msg = f"Source file does not exist: {abs_source_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.debug(f"Source file exists at: {abs_source_path}")

        # Create a temporary directory for the build
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.debug(f"Created temporary build directory: {temp_dir}")

            # Generate setup.py content
            setup_py_content = self._generate_setup_py(
                extension_name, source_file, extra_compile_args, define_macros
            )

            # Write setup.py to the temporary directory
            setup_py_path = os.path.join(temp_dir, "setup.py")
            logger.debug(f"Writing setup.py to: {setup_py_path}")
            with open(setup_py_path, "w") as f:
                f.write(setup_py_content)

            # Run the build command
            logger.info("Running setup.py build command")
            build_cmd = [sys.executable, "setup.py", "build_ext", "--inplace"]
            logger.debug(f"Build command: {' '.join(build_cmd)}")

            try:
                # Execute the build command
                logger.debug("Executing build subprocess")
                result = subprocess.run(
                    build_cmd,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
                logger.debug(f"Build stdout: {result.stdout}")
                logger.debug(f"Build stderr: {result.stderr}")

                # Determine the built extension path
                ext_suffix = self._get_extension_suffix()
                built_ext_path = os.path.join(
                    temp_dir, f"conditional_method", f"{extension_name}{ext_suffix}"
                )
                logger.debug(f"Looking for built extension at: {built_ext_path}")

                # If not found at the expected path, try to locate the file
                if not os.path.exists(built_ext_path):
                    logger.warning(
                        f"Extension not found at expected path: {built_ext_path}"
                    )
                    # Try to find it in the temp directory
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith(ext_suffix) and extension_name in file:
                                built_ext_path = os.path.join(root, file)
                                logger.info(f"Found extension at: {built_ext_path}")
                                break
                        if os.path.exists(built_ext_path):
                            break

                if not os.path.exists(built_ext_path):
                    error_msg = f"Extension not built. Files in temp directory: {os.listdir(temp_dir)}"
                    logger.error(error_msg)
                    # Check subdirectories
                    for root, dirs, files in os.walk(temp_dir):
                        logger.error(f"Directory {root}: {files}")
                    raise RuntimeError(error_msg)

                # Create the target directory if it doesn't exist
                target_dir = os.path.join(directory, "conditional_method")
                logger.debug(f"Ensuring target directory exists: {target_dir}")
                os.makedirs(target_dir, exist_ok=True)

                # Copy the built extension to the target directory
                target_path = os.path.join(target_dir, f"{extension_name}{ext_suffix}")
                logger.info(f"Copying extension from {built_ext_path} to {target_path}")
                shutil.copy2(built_ext_path, target_path)

                logger.info("Extension built and copied successfully")

            except subprocess.CalledProcessError as e:
                logger.error(f"Build command failed with exit code: {e.returncode}")
                logger.error(f"Build stdout: {e.stdout}")
                logger.error(f"Build stderr: {e.stderr}")
                raise RuntimeError(f"Failed to build extension: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected error during build: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    def _generate_setup_py(
        self,
        extension_name: str,
        source_file: str,
        extra_compile_args: List[str],
        define_macros: List[tuple],
    ) -> str:
        """
        Generate the setup.py content for building the extension.

        Args:
            extension_name: The name of the extension module
            source_file: The C source file path
            extra_compile_args: Additional compiler arguments
            define_macros: Preprocessor macro definitions

        Returns:
            The content of the setup.py file
        """
        logger.info(f"Generating setup.py for extension '{extension_name}'")
        logger.debug(f"Source file: {source_file}")
        logger.debug(f"Compiler args: {extra_compile_args}")
        logger.debug(f"Macros: {define_macros}")

        # Use the absolute path directly instead of trying to reconstruct it
        abs_source_path = os.path.abspath(source_file)
        logger.debug(f"Absolute source path: {abs_source_path}")

        # Format the extra_compile_args and define_macros for inclusion in setup.py
        formatted_compile_args = ", ".join([f'"{arg}"' for arg in extra_compile_args])
        logger.debug(f"Formatted compiler args: {formatted_compile_args}")

        formatted_macros = ", ".join(
            [f'("{name}", {repr(value)})' for name, value in define_macros]
        )
        logger.debug(f"Formatted macros: {formatted_macros}")

        setup_py = f"""
import os
from setuptools import setup, Extension

extension = Extension(
    "conditional_method.{extension_name}",
    sources=[r"{abs_source_path}"],  # Use raw string to handle Windows paths
    extra_compile_args=[{formatted_compile_args}],
    define_macros=[{formatted_macros}],
)

setup(
    name="conditional_method",
    version="{self.version}",
    ext_modules=[extension],
)
"""
        logger.debug(f"Generated setup.py content: {setup_py}")
        return setup_py

    def _get_extension_suffix(self) -> str:
        """
        Get the file extension suffix for the compiled extension.

        Returns:
            The extension suffix (e.g., '.so', '.pyd')
        """
        logger.info("Determining extension suffix")

        try:
            # Import here to avoid dependency issues during hook loading
            from distutils.sysconfig import get_config_var

            suffix = get_config_var("EXT_SUFFIX")
            logger.debug(f"get_config_var('EXT_SUFFIX') returned: {suffix}")

            if suffix is None:
                logger.warning(
                    "EXT_SUFFIX not found, falling back to platform-specific defaults"
                )
                # Fallback for older Python versions
                if sys.platform == "win32":
                    logger.debug("Using .pyd suffix for Windows")
                    suffix = ".pyd"
                else:
                    logger.debug("Using .so suffix for non-Windows platforms")
                    suffix = ".so"

            logger.info(f"Using extension suffix: {suffix}")
            return suffix

        except Exception as e:
            logger.error(f"Error determining extension suffix: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Ultimate fallback
            if sys.platform == "win32":
                logger.warning("Error occurred, defaulting to .pyd for Windows")
                return ".pyd"
            else:
                logger.warning(
                    "Error occurred, defaulting to .so for non-Windows platforms"
                )
                return ".so"

    def get_artifact_excludes(self) -> Dict[str, List[str]]:
        """
        Get patterns to exclude from artifact lists.
        
        Returns:
            A dictionary mapping build target names to lists of glob patterns to exclude
        """
        logger.info("Getting artifact excludes for targets")
        
        # For 'wheel' builds, exclude the source files as we'll include the compiled extension
        # For 'sdist' builds, we want to include the source files
        return {
            "wheel": ["**/*.c", "**/*.h"],  # Don't include C source files in wheels
            "sdist": [f"**/*{self._get_extension_suffix()}"]  # Don't include compiled extensions in sdist
        }
