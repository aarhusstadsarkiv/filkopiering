# import codecs
import os
import sys
import csv
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import date
import locale

from gooey import Gooey, GooeyParser


def setup_parser(cli: Any) -> Any:
    cli.add_argument(
        "source",
        metavar="Kilde",
        help=(
            "Sti til den overordnede mappe, hvorunder alle filerne findes"
            "(undermapper er tilladt)"
        ),
        widget="DirChooser",
        type=Path,
        gooey_options={
            "default_path": str(
                Path(
                    r"M:\Borgerservice-Biblioteker\Stadsarkivet\_DIGITALT ARKIV"
                )
            ),
            "full_width": True,
        },
    )
    cli.add_argument(
        "destination",
        metavar="Destination",
        help=(
            "Sti til mappen, hvortil filerne skal kopieres (mappen behøver ikke"
            " eksistere i forvejen)"
        ),
        widget="DirChooser",
        type=Path,
        gooey_options={
            "default_path": str(Path(Path.home(), "Downloads")),
            "full_width": True,
        },
    )
    cli.add_argument(
        "file",
        metavar="Csv-fil",
        help="Sti til csv-filen med fil-referencerne",
        widget="FileChooser",
        type=Path,
        gooey_options={"full_width": True},
    )
    cli.add_argument(
        "column",
        metavar="Kolonnenavn",
        help="Navnet på den kolonne i csv-filen, der indeholder fil-referencerne",
        gooey_options={"full_width": True},
    )
    cli.add_argument(
        "--delete",
        metavar="Slet oprindelige filer",
        action="store_true",
        help="Slet filerne fra deres oprindelige placering efter kopiering",
    )

    args = cli.parse_args()
    return args


def find_files(
    root_source: Path, filenames: List[str]
) -> Dict[str, List[str]]:

    print("Locating files referenced in csv-file...", flush=True)
    filenames_found: Dict[str, List[Path]] = {}

    for fname in os.listdir(root_source):
        if fname in filenames and os.path.isfile(
            os.path.join(root_source, fname)
        ):
            print(f"Found file: {fname}", flush=True)
            if fname not in filenames_found:
                filenames_found[fname] = [os.path.join(root_source, fname)]
            else:
                filenames_found[fname].append(os.path.join(root_source, fname))

    print(
        f"Finished locating {len(filenames_found)} of {len(filenames)} files.",
        flush=True,
    )
    print("")

    return filenames_found, [x for x in filenames if x not in filenames_found]


def copy_files(files_to_copy: Dict[str, List[str]], dest: Path) -> List[str]:
    files_copied: List[str] = []
    files_not_copied: List[str] = []

    print(f"Copying all {len(files_to_copy)} located files...", flush=True)

    for k, v in files_to_copy.items():
        if len(v) > 1:
            print(
                "Duplicate filename found. These files will not be copied and should be resolved:",
                flush=True,
            )
            for el in v:
                print(f"  {el}")
                files_not_copied.append(el)
            continue
        try:
            shutil.copy2(Path(v[0]), Path(dest, k))
            print(f"File copied to destination: {v[0]}")
        except Exception as e:
            print(f"Unable to copy file. {v[0]}: {e}", flush=True)
            files_not_copied.append(el)
        else:
            files_copied.append(v[0])

    print(
        f"Finished copying {len(files_copied)} of {len(files_to_copy)} file(s).",
        flush=True,
    )
    print("", flush=True)

    return files_copied, files_not_copied


def delete_files(files: List[str]) -> None:
    files_not_deleted: List[str] = []
    print(
        f"Deleting all {len(files)} succesfully copied file(s)...", flush=True
    )
    for f in files:
        try:
            Path(f).unlink()
            print(f"File deleted: {f}", flush=True)
        except Exception as e:
            print(f"Unable to delete file. {f}: {e}")
            files_not_deleted.append(f)

    print(
        f"Finished deleting {len(files) - len(files_not_deleted)} of {len(files)} file(s).",
        flush=True,
    )
    print("", flush=True)

    return files_not_deleted


@Gooey(
    program_name=f"Filkopiering, version {date.today().strftime('%Y-%m-%d')}",
    program_description="Værktøj til at kopiere filer fra csv-registreringer",
    default_size=(600, 700),
    # https://github.com/chriskiehl/Gooey/issues/520#issuecomment-576155188
    # necessary for pyinstaller to work in --windowed mode (no console)
    encoding=locale.getpreferredencoding(),
    show_restart_button=False,
    show_failure_modal=False,
    show_success_modal=False,
)
async def main() -> None:

    # General parser
    cli = GooeyParser(description="Filkopiering")
    args = setup_parser(cli)

    # Tests
    if not Path(args.source).is_dir():
        sys.exit(f"The source folder does not exist: {args.source}")

    if not Path(args.destination).is_dir():
        try:
            Path(args.destination).mkdir(parents=True)
            print("Destination folder created", flush=True)
        except Exception as e:
            sys.exit(f"Unable to create the destination folder: {e}")

    if not Path(args.file).is_file():
        sys.exit(f"The csv-file does not exist: {args.file}")

    filenames: List[str] = []
    column: str = args.column
    with open(Path(args.file), encoding="utf8") as ifile:
        reader = csv.DictReader(ifile)
        if not reader.fieldnames:
            sys.exit(f"The selected csv-file does not have a header column")
        if reader.fieldnames and column not in reader.fieldnames:
            sys.exit(f"The selected csv-file has no column named '{column}'")
        filenames = [d.get(column) for d in reader]

    print("All inputs valid.\n", flush=True)

    # Locate all files
    filenames_found, filenames_not_found = find_files(args.source, filenames)

    # Copy all files
    files_copied, files_not_copied = copy_files(
        filenames_found, args.destination
    )

    # Delete all files
    if args.delete and files_copied:
        files_not_deleted = delete_files(files_copied)

    # SUMMARY
    print("SUMMARY:", flush=True)

    # Locating status
    print(
        f"Found {len(filenames_found)} of {len(filenames)} referenced file(s).",
        flush=True,
    )
    if filenames_not_found:
        print(
            f"These {len(filenames_not_found)} file(s) could not be located and will not be copied:",
            flush=True,
        )
        for file in filenames_not_found:
            print(f"  {file}", flush=True)

    # Copy status
    print(
        f"Copied {len(files_copied)} of {len(filenames_found)} found file(s)."
    )
    if files_not_copied:
        print(
            f"These {len(files_not_copied)} file(s) could not be copied{' and is not deleted' if args.delete else ''}:",
            flush=True,
        )
        for file in files_not_copied:
            print(f"  {file}", flush=True)

    # Delete status
    if args.delete:
        print(
            f"Deleted {len(files_copied) - len(files_not_deleted)} of {len(files_copied)} copied file(s).",
            flush=True,
        )
        if files_not_deleted:
            print(
                f"These {len(files_not_deleted)} file(s) could not be deleted:",
                flush=True,
            )
            for f in files_not_deleted:
                print(f"  {f}", flush=True)
    else:
        print("No files were deleted.", flush=True)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
