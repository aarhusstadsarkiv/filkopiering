import codecs
import sys
import csv
import asyncio
import shutil

from pathlib import Path
from typing import List, Dict, Tuple, Any

from gooey import Gooey, GooeyParser

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
__version__ = "0.2.1"

utf8_stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
utf8_stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
if sys.stdout.encoding != "UTF-8":
    sys.stdout = utf8_stdout  # type: ignore
if sys.stderr.encoding != "UTF-8":
    sys.stderr = utf8_stderr  # type: ignore


@Gooey(
    program_name=f"Filkopiering, version {__version__}",
    program_description="Værktøj til at kopiere filer fra csv-registreringer",
    default_size=(600, 700),
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
        sys.exit(f"The sourcefolder does not exist: {args.source}")

    if not Path(args.destination).is_dir():
        try:
            Path(args.destination).mkdir(parents=True)
            print("Destinationfolder created", flush=True)
        except Exception as e:
            sys.exit(f"Unable to create the destinationfolder: {e}")

    if not Path(args.file).is_file():
        sys.exit(f"The csv-file does not exist: {args.file}")

    filenames: List = []
    column: str = args.column
    with open(Path(args.file), encoding="utf8") as ifile:
        reader = csv.DictReader(ifile)
        if reader.fieldnames and column not in reader.fieldnames:
            sys.exit(f"The selected csv-file has no column named '{column}'")
        filenames = [d.get(column) for d in reader]

    print("\nAll inputs valid.", flush=True)

    # process valid input
    # (
    #     detected_file_names,
    #     duplicated_file_names,
    # ) = walk_source_dir(args, filenames)
    # copy_files2(args.destination, detected_file_names, duplicated_file_names)

    # if duplicated_file_names:
    #     print_duplicate_file_names(duplicated_file_names, detected_file_names)

    # not_copied_files = list(
    #     set(filenames).difference(set(detected_file_names.keys()))
    # )

    files_found, filenames_not_found = find_files(args.source, filenames)
    if filenames_not_found:
        print(
            f"The following {len(filenames_not_found)} file(s) could not be "
            f"found and thus not copied:",
            flush=True,
        )
        for file in filenames_not_found:
            print(f"  {file}", flush=True)

    files_copied = copy_files(files_found, args.destination)

    if args.delete and files_copied:
        files_not_deleted = delete_files(files_copied)
        if files_not_deleted:
            print(
                f"Unable to delete the following {len(files_not_deleted)} file(s):",
                flush=True,
            )
            for f in files_not_deleted:
                print(f"  {f}", flush=True)


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
) -> Tuple[Dict[str, List[Path]], List[str]]:

    filenames_found: Dict[str, List[Path]] = {}
    for f in root_source.glob("**/*"):
        if f.is_file() and f.name in filenames:
            if f.name not in filenames_found:
                filenames_found[f.name] = [f]
            else:
                filenames_found[f.name].append(f)

    print(f"Finished locating {len(filenames_found)} file(s).", flush=True)
    return filenames_found, [x for x in filenames if x not in filenames_found]


def copy_files(files_to_copy: Dict[str, List[Path]], dest: Path) -> List[Path]:
    files_copied: List[Path] = []
    for k, v in files_to_copy.items():
        if len(v) > 1:
            print(
                "Duplicate filename found. These files will not be copied:",
                flush=True,
            )
            for el in v:
                print(f"  {el}")
            continue
        try:
            shutil.copy2(v[0], Path(dest, k))
        except Exception as e:
            print(f"Unable to copy file. {v[0]}: {e}")
        else:
            files_copied.append(v[0])

    print(f"Finished copying {len(files_copied)} file(s).", flush=True)
    return files_copied


def delete_files(files: List[Path]) -> List[Path]:
    files_not_deleted: List[Path] = []
    print("Deleting all succesfully copied files.", flush=True)
    for f in files:
        try:
            f.unlink()
        except Exception as e:
            print(f"Unable to delete file. {f}: {e}")
            files_not_deleted.append(f)

    print(
        f"Finished deleting {len(files) - len(files_not_deleted)} file(s).",
        flush=True,
    )
    return files_not_deleted


# def copy_files2(
#     destination: Any,
#     detected_file_names: Dict[str, List[Path]],
#     duplicated_file_names: List[str],
# ) -> None:
#     """
#     Copies the files in files_to_copy to their destination.

#     Args:
#         destination: Path. The root destination path.
#         detected_file_names: Dict[str, List[Path]]. A dictionary, where key is
#             a file name and value is a list of Paths representing a file with
#             the given file name in key.
#         duplicated_file_names: List[str]. A list of duplicated file names.
#     """
#     for filename in detected_file_names:
#         if filename not in duplicated_file_names:
#             try:
#                 shutil.copy(
#                     detected_file_names[filename][0],
#                     Path(destination, filename),
#                 )
#             except Exception as e:
#                 sys.exit(f"Unable to copy file to destination: {e}")
#     print("Finished copying.\n", flush=True)


# def walk_source_dir(
#     args, filenames
# ) -> Tuple[Dict[str, List[Path]], List[str]]:
#     """
#     Walks the source dir in order to find all the files to copy or delete.
#     In the delete case, the function also deletes the files.


#     Args:
#         args: Any.
#         filenames: List[str]. A list of names of files to copy.

#     Returns:
#         detected_file_names: Dict[str, List[Path]]. A dictionary,
#             where key is a file name and value is a list of Paths
#             representing a file with the given file name in key.
#         duplicated_file_names: List[str]. A list of the duplicated file names.
#     """
#     detected_file_names: Dict[str, List[Path]] = {}
#     duplicated_file_names: List[str] = []
#     # files_found: List[str] = []

#     for f in Path(args.source).glob("**/*"):
#         if f.is_file() and f.name in filenames:
#             # files_found.append(f.name)
#             if f.name in detected_file_names:
#                 duplicated_file_names.append(f.name)
#                 detected_file_names[f.name].append(f)
#             else:
#                 detected_file_names[f.name] = [f]
#         if args.delete:
#             try:
#                 f.unlink()
#                 print((f"{f.name} deleted from original path"), flush=True)
#             except Exception as e:
#                 sys.exit(f"Unable to delete file: {e}")

#     # missing_files: List = [f for f in filenames if f not in files_found]
#     return detected_file_names, duplicated_file_names


# def print_duplicate_file_names(
#     duplicated_file_names: List[str],
#     detected_file_names: Dict[str, List[Path]],
# ):
#     print(
#         f"Files with the following file names "
#         f"where found more than ones and thus not copied: ",
#         flush=True,
#     )
#     for name in duplicated_file_names:
#         print(f"{name} with paths: ", flush=True)
#         for path in detected_file_names[name]:
#             print(path, flush=True)
#     print("\n", flush=True)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
