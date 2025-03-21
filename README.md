# AutoSlug

Command-line tool to automatically rename files and directories to be URL-friendly. Ensures all names consist only of lowercase characters, numbers, and dashes (or underscores if the file type does not usually support dashes in file names). Ignores files with common naming conventions (such as `README` and `LICENSE`) and various artifacts. Does not modify leading periods and both leading and trailing underscores to support dotfiles and other special files. Supports formatting of detected numerical prefixes and shortening of names. See usage guide for details.

Ensures all [YAML](https://yaml.org/) files use the recommended `yaml` file extension instead of the commonly used `yml` extension.

Developed and maintained by Research Technology (RT), Tufts Technology Services (TTS), Tufts University.

## Installation

Install via [`pipx`](https://github.com/pypa/pipx) to use as a standalone command-line tool.

```
pipx install autoslug
```

## Usage

```
autoslug [options] <path>
```

### Positional Arguments

- `<path>`
  - path to the file or directory to process (processes current directory if omitted)

### Options

- `-h`/`--help`
  - display usage information and exit
- `-d`/`-n`/`--dry-run`
  - do not actually rename any files or directories
- `-f`/`--force`
  - disable protections and force processing
- `-q`/`--quiet`
  - suppress all output except errors (equivalent to setting `--log-level=ERROR`)
- `-v`/`--verbose`
  - report skipped and ignored paths in addition to renamed ones (equivalent to setting `--log-level=DEBUG`, overrides `--quiet`)
- `--error-limit <n>`
  - set exit level to failure if any paths exceed this character limit (will still attempt to process all paths)
- `--ignore-globs <glob>`
  - glob patterns to ignore in addition to
    - `**/__pycache__`
    - `**/.DS_Store`
    - `**/.git`
    - `**/.ipynb_checkpoints`
    - `**/LICENSE*`
    - `**/README*`
- `--ignore-root`
  - only process children of the specified path (implied when running in current directory)
- `--log-file <path>`
  - log output to specified file (all messages logged to file regardless of log level)
- `--log-level <level>`
  - set the console logging level to one of `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, or `CRITICAL` (overrides `--quiet` and `--verbose`)
- `--max-length <n>`
  - attempt to shorten file and directory names to not exceed this number of characters (excluding extension)
- `--no-dash-exts <ext>`
  - file extensions (without periods) where underscores should be used instead of dashes in addition to
    - `py`
- `--no-recurse`
  - do not recurse into subdirectories (only process specified path)
- `--num-digits <n>`
  - attempt to pad or round any existing numerical prefixes to consist of this many digits
- `--ok-exts <ext>`
  - file extensions (without periods) to recognize in addition to common MIME types and
    - `bat`
    - `cmd`
    - `ipynb`
    - `md`
    - `ps1`
    - `R`
    - `Rmd`
    - `rst`
    - `toml`
    - `yaml`
    - `yml`
- `--prefixes <prefix>`
  - file or directory name prefixes to leave unchanged in addition to
    - `_` (underscore)
    - `.` (period)
- `--suffixes <suffix>`
  - file or directory name suffixes (before extension) to leave unchanged in addition to
    - `_` (underscore)
- `--version`
  - display version information and exit
- `--warn-limit <n>`
  - output warning if path exceeds this character limit (does not affect exit level)
