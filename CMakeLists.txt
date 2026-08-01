cmake_minimum_required(VERSION 3.26)

project(higgs_combine_tool_wheel LANGUAGES CXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  message(FATAL_ERROR "higgs-combine-tool wheels currently support Linux x86_64 only")
endif()

find_package(Python REQUIRED COMPONENTS Interpreter)

execute_process(
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/prepare_root.py" --json
  RESULT_VARIABLE prepare_root_result
  OUTPUT_VARIABLE root_layout_json
  ERROR_VARIABLE prepare_root_stderr
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT prepare_root_result EQUAL 0)
  message(FATAL_ERROR "Could not prepare the PyPI ROOT wheel for CMake:\n${prepare_root_stderr}")
endif()
message(STATUS "${prepare_root_stderr}")

string(JSON root_package_dir GET "${root_layout_json}" root_package_dir)
string(JSON root_external_lib_dir GET "${root_layout_json}" root_external_lib_dir)

set(ROOT_DIR "${root_package_dir}/cmake" CACHE PATH "ROOT CMake package from the PyPI wheel" FORCE)
set(BUILD_TESTS OFF CACHE BOOL "Do not build upstream unit tests for a runtime wheel" FORCE)
set(USE_VDT OFF CACHE BOOL "The ROOT wheel does not require an external VDT package" FORCE)

# Install the native program and library inside the cms_combine package.  The
# Python modules keep their historical top-level HiggsAnalysis namespace.
set(CMAKE_INSTALL_BINDIR "cms_combine/bin" CACHE PATH "Wheel-private executables" FORCE)
set(CMAKE_INSTALL_LIBDIR "cms_combine/lib" CACHE PATH "Wheel-private libraries" FORCE)
set(CMAKE_INSTALL_INCLUDEDIR "cms_combine/cmssw/src" CACHE PATH "CMSSW-compatible headers" FORCE)
set(CMAKE_INSTALL_PYTHONDIR "." CACHE PATH "Wheel site-packages root" FORCE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH OFF)

add_subdirectory(vendor/CombinedLimit upstream-combine)

# ROOT is supplied by the separately installed `root` wheel.  Keep only
# relocatable paths in this wheel.  The sibling root.libs directory contains
# auditwheel-vendored dependencies needed while the final executable is linked.
set_target_properties(combine PROPERTIES
  INSTALL_RPATH "$ORIGIN/../lib;$ORIGIN/../../ROOT/lib"
)
set_target_properties(HiggsAnalysisCombinedLimit PROPERTIES
  INSTALL_RPATH "$ORIGIN;$ORIGIN/../../ROOT/lib"
)
target_link_options(combine PRIVATE "LINKER:-rpath-link,${root_external_lib_dir}")

# Package the small runtime model tables, but deliberately omit the 300+ MB CI
# and tutorial samples from the upstream repository.
install(
  DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/vendor/CombinedLimit/data/"
  DESTINATION "cms_combine/cmssw/src/HiggsAnalysis/CombinedLimit/data"
  PATTERN "*.root" EXCLUDE
)
