# Installation

```shell
pipx install git+https://github.com/aarhusstadsarkiv/digiarch.git
```

# Commands

* [digiarch](#digiarch)
    * [init](#digiarch-init)
    * [identify](#digiarch-identify)
        * [original](#digiarch-identify-original)
        * [master](#digiarch-identify-master)
    * [extract](#digiarch-extract)
    * [edit](#digiarch-edit)
        * [original](#digiarch-edit-original)
            * [action](#digiarch-edit-original-action)
                * [convert](#digiarch-edit-original-action-convert)
                * [extract](#digiarch-edit-original-action-extract)
                * [manual](#digiarch-edit-original-action-manual)
                * [ignore](#digiarch-edit-original-action-ignore)
                * [copy](#digiarch-edit-original-action-copy)
            * [processed](#digiarch-edit-original-processed)
            * [lock](#digiarch-edit-original-lock)
            * [rename](#digiarch-edit-original-rename)
            * [remove](#digiarch-edit-original-remove)
        * [master](#digiarch-edit-master)
            * [convert](#digiarch-edit-master-convert)
            * [processed](#digiarch-edit-master-processed)
            * [remove](#digiarch-edit-master-remove)
    * [upgrade](#digiarch-upgrade)
    * [help](#digiarch-help)
    * [completions](#digiarch-completions)

## digiarch

```
Usage: digiarch [OPTIONS] COMMAND [ARGS]...

  Identify files and generate the database used by other Aarhus City Archives
  tools.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init         Initialize the database.
  identify     Identify files.
  extract      Unpack archives.
  edit         Edit the database.
  upgrade      Upgrade the database.
  help         Show the help for a command.
  completions  Generate shell completions.
```

### digiarch init

```
Usage: digiarch init [OPTIONS] AVID_DIR

Options:
  --import FILE  Import an existing files.db
  --help         Show this message and exit.
```

### digiarch identify

```
Usage: digiarch identify [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  master    Identify master files.
  original  Identify original files.
```

#### digiarch identify original

```
Usage: digiarch identify original [OPTIONS] [QUERY]

Options:
  --siegfried-path FILE           The path to the Siegfried executable.  [env
                                  var: SIEGFRIED_PATH]
  --siegfried-home DIRECTORY      The path to the Siegfried home folder.  [env
                                  var: SIEGFRIED_HOME; required]
  --siegfried-signature [pronom|loc|tika|freedesktop|pronom-tika-loc|deluxe|archivematica]
                                  The signature file to use with Siegfried.
                                  [default: pronom]
  --actions FILE                  Path to a YAML file containing file format
                                  actions.  [env var: DIGIARCH_ACTIONS]
  --custom-signatures FILE        Path to a YAML file containing custom
                                  signature specifications.  [env var:
                                  DIGIARCH_CUSTOM_SIGNATURES]
  --exclude TEXT                  File and folder names to exclude.
                                  [multiple]
  --batch-size INTEGER RANGE      Amount of files to identify at a time.
                                  [default: 100; x>=1]
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

#### digiarch identify master

```
Usage: digiarch identify master [OPTIONS] [QUERY]

Options:
  --siegfried-path FILE           The path to the Siegfried executable.  [env
                                  var: SIEGFRIED_PATH]
  --siegfried-home DIRECTORY      The path to the Siegfried home folder.  [env
                                  var: SIEGFRIED_HOME; required]
  --siegfried-signature [pronom|loc|tika|freedesktop|pronom-tika-loc|deluxe|archivematica]
                                  The signature file to use with Siegfried.
                                  [default: pronom]
  --actions FILE                  Path to a YAML file containing master files
                                  convert actions.  [env var:
                                  DIGIARCH_MASTER_ACTIONS]
  --custom-signatures FILE        Path to a YAML file containing custom
                                  signature specifications.  [env var:
                                  DIGIARCH_CUSTOM_SIGNATURES]
  --batch-size INTEGER RANGE      Amount of files to identify at a time.
                                  [default: 100; x>=1]
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

### digiarch extract

```
Usage: digiarch extract [OPTIONS] [QUERY]

  Unpack archives and identify files therein.

  Files are unpacked recursively, i.e., if an archive contains another
  archive, this will be unpacked as well.

  Archives with unrecognized extraction tools will be set to manual mode.

  To see the which files will be unpacked (but not their contents) without
  unpacking them, use the --dry-run option.

Options:
  --siegfried-path FILE           The path to the Siegfried executable.  [env
                                  var: SIEGFRIED_PATH]
  --siegfried-home DIRECTORY      The path to the Siegfried home folder.  [env
                                  var: SIEGFRIED_HOME; required]
  --siegfried-signature [pronom|loc|tika|freedesktop|pronom-tika-loc|deluxe|archivematica]
                                  The signature file to use with Siegfried.
                                  [default: pronom]
  --actions FILE                  Path to a YAML file containing file format
                                  actions.  [env var: DIGIARCH_ACTIONS]
  --custom-signatures FILE        Path to a YAML file containing custom
                                  signature specifications.  [env var:
                                  DIGIARCH_CUSTOM_SIGNATURES]
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

### digiarch edit

```
Usage: digiarch edit [OPTIONS] COMMAND [ARGS]...

  Edit the files' database.

  The ROOT argument in the edit subcommands is a folder that contains a
  _metadata/files.db database, not the _metadata folder itself.

  The QUERY argument uses a simple search syntax.
  @<field> will match a specific field, the following are supported: uuid,
  checksum, puid, relative_path, action, warning, processed, lock.
  @null and @notnull will match columns with null and not null values respectively.
  @true and @false will match columns with true and false values respectively.
  @like toggles LIKE syntax for the values following it in the same column.
  @file toggles file reading for the values following it in the same column: each
  value will be considered as a file path and values will be read from the lines
  in the given file (@null, @notnull, @true, and @false in files are not supported).
  Changing to a new @<field> resets like and file toggles. Values for the same
  column will be matched with OR logic, while values from different columns will
  be matched with AND logic.

  Every edit subcommand requires a REASON argument that will be used in the
  database log to explain the reason behind the edit.

  Query Examples
  --------------

  @uuid @file uuids.txt @warning @notnull = (uuid = ? or uuid = ? or uuid = ?)
  and (warning is not null)

  @relative_path @like %.pdf @lock @true = (relative_path like ?) and (lock is
  true)

  @action convert @relative_path @like %.pdf %.msg = (action = ?) and
  (relative_path like ? or relative_path like ?)

Options:
  --help  Show this message and exit.

Commands:
  original  Edit original files.
  master    Edit master files.
```

#### digiarch edit original

```
Usage: digiarch edit original [OPTIONS] COMMAND [ARGS]...

  Edit original files.

Options:
  --help  Show this message and exit.

Commands:
  action     Change file actions.
  processed  Set original files as processed.
  lock       Lock files.
  rename     Change file extensions.
  remove     Remove files.
```

##### digiarch edit original action

```
Usage: digiarch edit original action [OPTIONS] COMMAND [ARGS]...

  Change file actions.

Options:
  --help  Show this message and exit.

Commands:
  convert  Set convert action.
  extract  Set extract action.
  manual   Set manual action.
  ignore   Set ignore action.
  copy     Copy action from a format.
```

###### digiarch edit original action convert

```
Usage: digiarch edit original action convert [OPTIONS] QUERY REASON

  Set files' action to "convert".

  The --output option may be omitted when using the "copy" tool.

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --tool TEXT    The tool to use for conversion.  [required]
  --output TEXT  The output of the converter.  [required for tools other than
                 "copy"]
  --lock         Lock the edited files.
  --dry-run      Show changes without committing them.
  --help         Show this message and exit.
```

###### digiarch edit original action extract

```
Usage: digiarch edit original action extract [OPTIONS] QUERY REASON

  Set files' action to "extract".

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --tool TEXT       The tool to use for extraction.  [required]
  --extension TEXT  The extension the file must have for extraction to
                    succeed.
  --lock            Lock the edited files.
  --dry-run         Show changes without committing them.
  --help            Show this message and exit.
```

###### digiarch edit original action manual

```
Usage: digiarch edit original action manual [OPTIONS] QUERY REASON

  Set files' action to "manual".

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --reason TEXT   The reason why the file must be processed manually.
                  [required]
  --process TEXT  The steps to take to process the file.  [required]
  --lock          Lock the edited files.
  --dry-run       Show changes without committing them.
  --help          Show this message and exit.
```

###### digiarch edit original action ignore

```
Usage: digiarch edit original action ignore [OPTIONS] QUERY REASON

  Set files' action to "ignore".

  Template must be one of:
  * text
      * empty
      * password-protected
      * corrupted
      * duplicate
      * not-preservable
      * not-convertable
      * extracted-archive
      * temporary-file

  The --reason option may be omitted when using a template other than "text".

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --template TEMPLATE  The template type to use.  [required]
  --reason TEXT        The reason why the file is ignored.  [required for
                       "text" template]
  --lock               Lock the edited files.
  --dry-run            Show changes without committing them.
  --help               Show this message and exit.
```

###### digiarch edit original action copy

```
Usage: digiarch edit original action copy [OPTIONS] QUERY PUID
                                          {convert|extract|manual|ignore}
                                          REASON

  Set files' action by copying it from an existing format.

  Supported actions are:
  * convert
  * extract
  * manual
  * ignore

  If no actions file is give with --actions, the latest version will be
  downloaded from GitHub.

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --actions FILE  Path to a YAML file containing file format actions.  [env
                  var: DIGIARCH_ACTIONS]
  --lock          Lock the edited files.
  --dry-run       Show changes without committing them.
  --help          Show this message and exit.
```

##### digiarch edit original processed

```
Usage: digiarch edit original processed [OPTIONS] QUERY REASON

  Set original files as processed.

  To set files as unprocessed, use the --unprocessed option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --processed / --unprocessed  Set files as processed or unprocessed.
                               [default: processed]
  --dry-run                    Show changes without committing them.
  --help                       Show this message and exit.
```

##### digiarch edit original lock

```
Usage: digiarch edit original lock [OPTIONS] QUERY REASON

  Lock original files from being edited by reidentify.

  To unlock files, use the --unlock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --lock / --unlock  Lock or unlock files.  [default: lock]
  --dry-run          Show changes without committing them.
  --help             Show this message and exit.
```

##### digiarch edit original rename

```
Usage: digiarch edit original rename [OPTIONS] QUERY EXTENSION REASON

  Change the extension of one or more files in the files' database for the
  ROOT folder to EXTENSION.

  To see the changes without committing them, use the --dry-run option.

  The --replace and --replace-all options will only replace valid suffixes
  (i.e., matching the expression \.[a-zA-Z0-9]+).

  The --append option will not add the new extension if it is already present.

Options:
  --append       Append the new extension.  [default]
  --replace      Replace the last extension.
  --replace-all  Replace all extensions.
  --dry-run      Show changes without committing them.
  --help         Show this message and exit.
```

##### digiarch edit original remove

```
Usage: digiarch edit original remove [OPTIONS] QUERY REASON

  Remove one or more original files in the files' database for the ROOT folder
  to EXTENSION.

  Using the --delete option removes the files from the disk.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --delete   Remove selected files from the disk.
  --dry-run  Show changes without committing them.
  --help     Show this message and exit.
```

#### digiarch edit master

```
Usage: digiarch edit master [OPTIONS] COMMAND [ARGS]...

  Edit master files.

Options:
  --help  Show this message and exit.

Commands:
  convert    Set access convert action.
  processed  Set master files as processed.
  remove     Remove files.
```

##### digiarch edit master convert

```
Usage: digiarch edit master convert [OPTIONS] {access|statutory} QUERY REASON

  Set master files' convert action.

  The --output option may be omitted when using the "copy" tool.

  To lock the file(s) after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --tool TEXT    The tool to use for conversion.  [required]
  --output TEXT  The output of the converter.  [required for tools other than
                 "copy"]
  --lock         Lock the edited files.
  --dry-run      Show changes without committing them.
  --help         Show this message and exit.
```

##### digiarch edit master processed

```
Usage: digiarch edit master processed [OPTIONS] QUERY REASON

  Set master files as processed.

  To set files as unprocessed, use the --unprocessed option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --processed / --unprocessed  Set files as processed or unprocessed.
                               [default: processed]
  --dry-run                    Show changes without committing them.
  --help                       Show this message and exit.
```

##### digiarch edit master remove

```
Usage: digiarch edit master remove [OPTIONS] QUERY REASON

  Remove one or more master files in the files' database for the ROOT folder
  to EXTENSION.

  Files are delete from the database and the disk.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --reset-processed  Reset processed status of parent files.
  --dry-run          Show changes without committing them.
  --help             Show this message and exit.
```

### digiarch upgrade

```
Usage: digiarch upgrade [OPTIONS]

  Upgrade the files' database to the latest version of acacore.

  When using --backup, a copy of the current database version will be created
  in the same folder with the name "avid-{version}.db". The copy will not be
  created if the database is already at the latest version.

Options:
  --backup / --no-backup  Backup current version.  [default: backup]
  --help                  Show this message and exit.
```

### digiarch help

```
Usage: digiarch help [OPTIONS] [COMMANDS]...

  Show the help for a command.

Options:
  --help  Show this message and exit.
```

### digiarch completions

```
Usage: digiarch completions [OPTIONS] {bash|fish|zsh}

  Generate tab-completion scripts for your shell.

  The generated completion must be saved in the correct location for it to be
  recognized and used by the shell.

  Supported shells are:
  * bash  Bourne Again Shell
      * fish      Friendly Interactive Shell
      * zsh       Z shell

Options:
  --help  Show this message and exit.
```