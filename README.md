# Commands

* [digiarch](#digiarch)
    * [init](#digiarch-init)
    * [identify](#digiarch-identify)
        * [original](#digiarch-identify-original)
        * [master](#digiarch-identify-master)
        * [access](#digiarch-identify-access)
        * [statutory](#digiarch-identify-statutory)
    * [extract](#digiarch-extract)
    * [edit](#digiarch-edit)
        * [original](#digiarch-edit-original)
            * [puid](#digiarch-edit-original-puid)
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
            * [puid](#digiarch-edit-master-puid)
            * [convert](#digiarch-edit-master-convert)
            * [processed](#digiarch-edit-master-processed)
            * [remove](#digiarch-edit-master-remove)
        * [access](#digiarch-edit-access)
            * [remove](#digiarch-edit-access-remove)
        * [statutory](#digiarch-edit-statutory)
            * [remove](#digiarch-edit-statutory-remove)
        * [rollback](#digiarch-edit-rollback)
    * [manual](#digiarch-manual)
        * [extract](#digiarch-manual-extract)
        * [convert](#digiarch-manual-convert)
    * [finalize](#digiarch-finalize)
        * [doc-collections](#digiarch-finalize-doc-collections)
        * [doc-index](#digiarch-finalize-doc-index)
    * [search](#digiarch-search)
        * [original](#digiarch-search-original)
        * [master](#digiarch-search-master)
        * [access](#digiarch-search-access)
        * [statutory](#digiarch-search-statutory)
    * [info](#digiarch-info)
    * [log](#digiarch-log)
    * [upgrade](#digiarch-upgrade)
    * [help](#digiarch-help)
    * [completions](#digiarch-completions)

## digiarch

```
Usage: digiarch [OPTIONS] COMMAND [ARGS]...

  Indentify files and process AVID archives.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init         Initialize the database.
  identify     Identify files.
  extract      Unpack archives.
  edit         Edit the database.
  manual       Perform actions manually.
  finalize     Finalize for delivery.
  search       Search the database.
  info         Database information.
  log          Display the event log.
  upgrade      Upgrade the database.
  help         Show the help for a command.
  completions  Generate shell completions.
```

### digiarch init

```
Usage: digiarch init [OPTIONS] AVID_DIR

  Initialize the AVID database in a directory (AVID_DIR).

  The directory is checked to make sure it has the structure expected of an
  AVID archive.

  The --import option allows to import original and master files from a
  files.db database generated by version v4.1.12 of digiarch (acacore v3.3.3).
  A pre-acacore version of the database can also be used if it contains a
  'Files' table with a 'path' column, but some master files may be missing.

Options:
  --import FILE  Import an existing files.db
  --help         Show this message and exit.
```

### digiarch identify

```
Usage: digiarch identify [OPTIONS] COMMAND [ARGS]...

  Identify files in the archive.

Options:
  --help  Show this message and exit.

Commands:
  original   Identify original files.
  master     Identify master files.
  access     Identify access files.
  statutory  Identify statutory files.
```

#### digiarch identify original

```
Usage: digiarch identify original [OPTIONS] [QUERY]

  Identify files in the OriginalDocuments directory.

  Each file is identified with Siegfried and an action is assigned to it.
  Files that are already in the database are not processed.

  If the QUERY argument is given, then files in the database matching the
  query will be re-identified.

  For details on the QUERY argument, see the edit command.

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
  --ignore-lock                   Re-identify locked files.
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

#### digiarch identify master

```
Usage: digiarch identify master [OPTIONS] [QUERY]

  Identify files in the MasterDocuments directory.

  Files are taken from the database, any other file existing in the
  MasterDocuments directory will be ignored. Each file is identified with
  Siegfried and convert actions for access and statutory files are assigned to
  it.

  If the QUERY argument is given, then only the files matching the query will
  be identified or re-identified.

  For details on the QUERY argument, see the edit command.

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

#### digiarch identify access

```
Usage: digiarch identify access [OPTIONS] [QUERY]

  Identify files in the AccessDocuments directory.

  Files are taken from the database, any other file existing in the
  AccessDocuments directory will be ignored. Each file is identified with
  Siegfried.

  If the QUERY argument is given, then only the files matching the query will
  be identified or re-identified.

  For details on the QUERY argument, see the edit command.

Options:
  --siegfried-path FILE           The path to the Siegfried executable.  [env
                                  var: SIEGFRIED_PATH]
  --siegfried-home DIRECTORY      The path to the Siegfried home folder.  [env
                                  var: SIEGFRIED_HOME; required]
  --siegfried-signature [pronom|loc|tika|freedesktop|pronom-tika-loc|deluxe|archivematica]
                                  The signature file to use with Siegfried.
                                  [default: pronom]
  --batch-size INTEGER RANGE      Amount of files to identify at a time.
                                  [default: 100; x>=1]
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

#### digiarch identify statutory

```
Usage: digiarch identify statutory [OPTIONS] [QUERY]

  Identify files in the Documents directory.

  Files are taken from the database, any other file existing in the Documents
  directory will be ignored. Each file is identified with Siegfried.

  If the QUERY argument is given, then only the files matching the query will
  be identified or re-identified.

  For details on the QUERY argument, see the edit command.

Options:
  --siegfried-path FILE           The path to the Siegfried executable.  [env
                                  var: SIEGFRIED_PATH]
  --siegfried-home DIRECTORY      The path to the Siegfried home folder.  [env
                                  var: SIEGFRIED_HOME; required]
  --siegfried-signature [pronom|loc|tika|freedesktop|pronom-tika-loc|deluxe|archivematica]
                                  The signature file to use with Siegfried.
                                  [default: pronom]
  --batch-size INTEGER RANGE      Amount of files to identify at a time.
                                  [default: 100; x>=1]
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

### digiarch extract

```
Usage: digiarch extract [OPTIONS] [QUERY]

  Unpack archives in OriginalDocuments and identify files therein.

  Files are unpacked recursively, i.e., if an archive contains another
  archive, this will be unpacked as well.

  Archives with unrecognized extraction tools will be set to manual mode.

  To see the which files will be unpacked (but not their contents) without
  unpacking them, use the --dry-run option.

  Extracted filenames longer than 20 characters will be trimmed and partially
  prefixed with a unique hash based on the original name.

  Use the QUERY argument to specify which files should be unpacked. For
  details on the QUERY argument, see the edit command.

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

  Edit the files in the database.

  The QUERY argument uses a simple search syntax.
  @<field> will match a specific field, the following are supported: uuid,
  checksum, puid, relative_path, action, warning, processed, lock.
  @null and @notnull will match columns with null and not null values respectively.
  @true and @false will match columns with true and false values respectively.
  @like toggles LIKE syntax for the values following it in the same column.
  @file toggles file reading for the values following it in the same column: each
  value will be considered as a file path and values will be read from the lines
  in the given file (@null, @notnull, @true, @false, and @like are not supported when using @file).
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
  original   Edit original files.
  master     Edit master files.
  access     Edit access files.
  statutory  Edit statutory files.
  rollback   Roll back edits.
```

#### digiarch edit original

```
Usage: digiarch edit original [OPTIONS] COMMAND [ARGS]...

  Edit original files.

Options:
  --help  Show this message and exit.

Commands:
  puid       Change PUID.
  action     Change actions of original files.
  processed  Set original files as processed.
  lock       Lock files.
  rename     Change file extensions.
  remove     Remove files.
```

##### digiarch edit original puid

```
Usage: digiarch edit original puid [OPTIONS] PUID QUERY REASON

  Change PUID of original files.

  To lock the files after editing them, use the --lock option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --lock     Lock the edited files.
  --dry-run  Show changes without committing them.
  --help     Show this message and exit.
```

##### digiarch edit original action

```
Usage: digiarch edit original action [OPTIONS] COMMAND [ARGS]...

  Change actions of original files.

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

  Set the action of original files matching the QUERY argument to "convert".

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

  Set the action of original files matching the QUERY argument to "extract".

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

  Set the action of original files matching the QUERY argument to "manual".

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

  Set the action of original files matching the QUERY argument to "ignore".

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

  Set the action of original files matching the QUERY argument by copying it
  from an existing format.

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

  Set original files matching the QUERY argument as processed.

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

  Lock original files matching the QUERY argument from being edited by
  reidentify.

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

  Change the extension of one or more files in OriginalDocuments matching the
  QUERY argument to EXTENSION.

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

  Remove one or more files in OriginalDocuments matching the QUERY argument.

  Using the --delete option removes the files from the disk.

  All children files (master, access, and statutory) are removed recursively
  from both the database and the disk regardless of the --delete option.

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
  puid       Change PUID.
  convert    Set access convert action.
  processed  Set master files as processed.
  remove     Remove files.
```

##### digiarch edit master puid

```
Usage: digiarch edit master puid [OPTIONS] PUID QUERY REASON

  Change PUID of master files.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --dry-run  Show changes without committing them.
  --help     Show this message and exit.
```

##### digiarch edit master convert

```
Usage: digiarch edit master convert [OPTIONS] {access|statutory} QUERY REASON

  Set the convert actions of master files matching the QUERY argument.

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
Usage: digiarch edit master processed [OPTIONS] QUERY {access|statutory}
                                      REASON

  Set master files matching the QUERY argument as processed for the relevant
  target (access or statutory).

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

  Remove one or more files in MasterDocuments matching the QUERY argument.

  All matching files and their children (access, and statutory) are removed
  recursively from both the database and the disk.

  To set the parent files in OriginalDocuments to unprocessed, use the
  --reset-processed option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --reset-processed  Reset processed status of parent files.
  --dry-run          Show changes without committing them.
  --help             Show this message and exit.
```

#### digiarch edit access

```
Usage: digiarch edit access [OPTIONS] COMMAND [ARGS]...

  Edit access files.

Options:
  --help  Show this message and exit.

Commands:
  remove  Remove files.
```

##### digiarch edit access remove

```
Usage: digiarch edit access remove [OPTIONS] QUERY REASON

  Remove one or more files in AccessDocuments matching the QUERY argument.

  All matching files are removed from both the database and the disk.

  To set the parent files in MasterDocuments to unprocessed, use the --reset-
  processed option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --reset-processed  Reset processed status of parent files.
  --dry-run          Show changes without committing them.
  --help             Show this message and exit.
```

#### digiarch edit statutory

```
Usage: digiarch edit statutory [OPTIONS] COMMAND [ARGS]...

  Edit statutory files.

Options:
  --help  Show this message and exit.

Commands:
  remove  Remove files.
```

##### digiarch edit statutory remove

```
Usage: digiarch edit statutory remove [OPTIONS] QUERY REASON

  Remove one or more files in Documents matching the QUERY argument.

  All matching files are removed from both the database and the disk.

  To set the parent files in MasterDocuments to unprocessed, use the --reset-
  processed option.

  To see the changes without committing them, use the --dry-run option.

  For details on the QUERY argument, see the edit command.

Options:
  --reset-processed  Reset processed status of parent files.
  --dry-run          Show changes without committing them.
  --help             Show this message and exit.
```

#### digiarch edit rollback

```
Usage: digiarch edit rollback [OPTIONS] RUN

  Roll back changes.

  RUN can be a run index (1 for the previous run, 2 for the run before that,
  and so on), an index slice (e.g., 2:4 to roll back the second to last
  through the fourth to last run) or the timestamp of a run in the format
  '%Y-%m-%dT%H:%M:%S' or '%Y-%m-%dT%H:%M:%S.%f'.

  Runs that have already been rolled back (even if just partially) are
  ignored. To include partially rolled-back runs use the --resume-partial
  option.

  To see the changes without committing them, use the --dry-run option.

  To see a list of commands that can be rolled back, use the --list-commands
  option.

Options:
  --resume-partial  Ignore partially rolled back runs.
  --list-commands   List commands that can be rolled back.
  --dry-run         Show changes without committing them.
  --help            Show this message and exit.
```

### digiarch manual

```
Usage: digiarch manual [OPTIONS] COMMAND [ARGS]...

  Perform complex actions manually when the automated tools fail or when one
  is not available.

Options:
  --help  Show this message and exit.

Commands:
  convert  Add converted files.
  extract  Add extracted files.
```

#### digiarch manual extract

```
Usage: digiarch manual extract [OPTIONS] PARENT FILE...

  Manually add files extracted from an archive, and assign them the PARENT
  UUID.

  The given FILEs can be single files or folders and must be located inside
  OriginalDocuments. All of them will be interpreted as direct children of the
  PARENT file, so archive files should be left unextracted for further
  processing with either extract or manual extract.

  To exclude children files when using a folder as target, use the --exclude
  option.

  If the files are not already in the database they will be added without
  identification. Run the identify original command to assign them a PUID and
  action.

  If the files are in the database their parent value will be set to ORIGINAL
  unless they already have one assigned, in which case they will be ignored.
  Run the identify command to assign a PUID and action to newly-added files.

  To see the changes without committing them, use the --dry-run option.

Options:
  --exclude TEXT  File and folder names to exclude.  [multiple]
  --dry-run       Show changes without committing them.
  --help          Show this message and exit.
```

#### digiarch manual convert

```
Usage: digiarch manual convert [OPTIONS] ORIGINAL {master|access|statutory}
                               FILE...

  Manually add converted files with ORIGINAL UUID as their parent.

  Depending on the TARGET, a different type of ORIGINAL file will be needed:
  * "master": original file parent
  * "access": master file parent
  * "statutory": master file parent

  The given FILEs must be located inside the MasterDocuments, AccessDocuments,
  or Documents folder depending on the TARGET.

  If the files are already in the database they will be ignored. Run the
  identify command to assign a PUID (and action where applicable) to newly-
  added files.

  To see the changes without committing them, use the --dry-run option.

Options:
  --dry-run  Show changes without committing them.
  --help     Show this message and exit.
```

### digiarch finalize

```
Usage: digiarch finalize [OPTIONS] COMMAND [ARGS]...

  Perform the necessary opration to ready the AVID directory for delivery.

  The changes should be performed in the following order:
  * doc-collections
  * doc-index (TBA)
  * av-db (TBA)

Options:
  --help  Show this message and exit.

Commands:
  doc-collections  Create docCollections.
  doc-index        Create docIndex.
```

#### digiarch finalize doc-collections

```
Usage: digiarch finalize doc-collections [OPTIONS]

  Rearrange files in Documents using docCollections.

  If the process is interrupted, all changes are rolled back, but the newly
  named files can be recovered using the --resume option when the command is
  run next. The option should only ever be used if NO other changes have
  occured to the files or the database. The default behaviour is to remove any
  leftover files and start the process anew.

  To change the number of documents in each docCollection directory, use the
  --docs-in-collection option.

  To see the changes without committing them, use the --dry-run option.

Options:
  --docs-in-collection INTEGER RANGE
                                  The maximum number of documents to put in
                                  each docCollection.  [default: 10000; x>=1]
  --resume / --no-resume          Resume a previously interrupted
                                  rearrangement.
  --dry-run                       Show changes without committing them.
  --help                          Show this message and exit.
```

#### digiarch finalize doc-index

```
Usage: digiarch finalize doc-index [OPTIONS]

  Create the docIndex.xml file from statutory files.

  To change the number of documents in each docCollection directory, use the
  --docs-in-collection option, ensuring the same number has been used to
  rearrange statutory files with the finalize doc-collections command.

  To change the number of documents in each mediaID collection, use the
  --docs-in-media option, ensuring that it is a multiple of the --docs-in-
  collection value to avoid splitting docCollections across multiple mediaIDs.

Options:
  --media-id TEXT                 The mediaID value.
  --docs-in-collection INTEGER RANGE
                                  The maximum number of documents to put in
                                  each docCollection.  [default: 10000; x>=1]
  --docs-in-media INTEGER RANGE   The maximum number of documents to put in
                                  each mediaID collection.  [x>=1]
  --help                          Show this message and exit.
```

### digiarch search

```
Usage: digiarch search [OPTIONS] COMMAND [ARGS]...

  Search files in the database.

Options:
  --help  Show this message and exit.

Commands:
  access     Search access files.
  master     Search master files.
  original   Search original files.
  statutory  Search statutory files.
```

#### digiarch search original

```
Usage: digiarch search original [OPTIONS] [QUERY]

  Search among the original files in the database.

  The wollowing query fields are supported:
  * uuid
  * checksum
  * puid
  * relative_path
  * action
  * warning
  * is_binary
  * processed
  * lock
  * original_path

  For details on the QUERY argument, see the edit command.

Options:
  --sort [relative_path|puid|checksum|action]
                                  Choose sorting column,  [default:
                                  relative_path]
  --order [asc|desc]              Choose sorting order.  [default: asc]
  --limit INTEGER                 Limit number of results.  [default: 100;
                                  x>=1]
  --offset INTEGER                Offset number of results.  [default: 0;
                                  x>=0]
  --help                          Show this message and exit.
```

#### digiarch search master

```
Usage: digiarch search master [OPTIONS] [QUERY]

  Search among the master files in the database.

  The wollowing query fields are supported:
  * uuid
  * checksum
  * puid
  * relative_path
  * warning
  * is_binary
  * processed
  * original_uuid

  For details on the QUERY argument, see the edit command.

Options:
  --sort [relative_path|puid|checksum]
                                  Choose sorting column,  [default:
                                  relative_path]
  --order [asc|desc]              Choose sorting order.  [default: asc]
  --limit INTEGER                 Limit number of results.  [default: 100;
                                  x>=1]
  --offset INTEGER                Offset number of results.  [default: 0;
                                  x>=0]
  --help                          Show this message and exit.
```

#### digiarch search access

```
Usage: digiarch search access [OPTIONS] [QUERY]

  Search among the access files in the database.

  The wollowing query fields are supported:
  * uuid
  * checksum
  * puid
  * relative_path
  * warning
  * is_binary
  * original_uuid

  For details on the QUERY argument, see the edit command.

Options:
  --sort [relative_path|puid|checksum]
                                  Choose sorting column,  [default:
                                  relative_path]
  --order [asc|desc]              Choose sorting order.  [default: asc]
  --limit INTEGER                 Limit number of results.  [default: 100;
                                  x>=1]
  --offset INTEGER                Offset number of results.  [default: 0;
                                  x>=0]
  --help                          Show this message and exit.
```

#### digiarch search statutory

```
Usage: digiarch search statutory [OPTIONS] [QUERY]

  Search among the statutory files in the database.

  The wollowing query fields are supported:
  * uuid
  * checksum
  * puid
  * relative_path
  * warning
  * is_binary
  * original_uuid

  For details on the QUERY argument, see the edit command.

Options:
  --sort [relative_path|puid|checksum]
                                  Choose sorting column,  [default:
                                  relative_path]
  --order [asc|desc]              Choose sorting order.  [default: asc]
  --limit INTEGER                 Limit number of results.  [default: 100;
                                  x>=1]
  --offset INTEGER                Offset number of results.  [default: 0;
                                  x>=0]
  --help                          Show this message and exit.
```

### digiarch info

```
Usage: digiarch info [OPTIONS]

  Display information about the database.

Options:
  --help  Show this message and exit.
```

### digiarch log

```
Usage: digiarch log [OPTIONS]

  Display the event log.

  Start events will display the index to be used to roll back the of that
  command.

Options:
  --runs-only         Only show start/end events.
  --order [asc|desc]  Choose sorting order.  [default: asc]
  --limit INTEGER     Limit number of results.  [default: 100; x>=1]
  --help              Show this message and exit.
```

### digiarch upgrade

```
Usage: digiarch upgrade [OPTIONS]

  Upgrade the database.

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

  Generate completion scripts for your shell.

  The generated completion must be saved in the correct location for it to be
  recognized and used by the shell.

  Supported shells are:
  * bash  Bourne Again Shell
  * fish  Friendly Interactive Shell
  * zsh   Z shell

Options:
  --help  Show this message and exit.
```
