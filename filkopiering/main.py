import codecs
import sys
import csv
import asyncio
import shutil

from pathlib import Path
from typing import List
from typing import Dict
from typing import Tuple

from gooey import Gooey, GooeyParser

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
__version__ = "0.1.0"

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
        print(
            "The destinationfolder does not exist. Trying to create it...",
            flush=True,
        )
        try:
            Path(args.destination).mkdir(parents=True)
            print("Destinationfolder created", flush=True)
        except Exception as e:
            sys.exit(f"Unable to create the destinationfolder: {e}")

    if not Path(args.file).is_file():
        sys.exit(f"The csv-file does not exist: {args.file}")

    filenames: List = []
    column: str = args.column

    with open(Path(args.file), encoding='utf8') as ifile:
        reader = csv.DictReader(ifile)
        if reader.fieldnames and column not in reader.fieldnames:
            sys.exit(f"The selected csv-file has no column named '{column}'")

        filenames = [d.get(column) for d in reader]
        
    print("All inputs valid. Copying files...", flush=True)
    
    files_to_copy, detected_file_names, duplicate_file_names = walk_source_dir(args, filenames)    
    copy_files(args.destination, files_to_copy)

    if duplicate_file_names:
            print_duplicate_file_names(duplicate_file_names)

    not_copied_files = list(set(detected_file_names).difference(filenames))
    print("The following files could not be found and thus not copied: ", flush=True)
    for file in not_copied_files:
        print(file)

def setup_parser(cli) -> any:
    cli.add_argument(
        "source",
        metavar="Kilde",
        help="Sti til den overordnede mappe, hvorunder alle filerne findes \
            (undermapper er tilladt)",
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
        help="Sti til mappen, hvortil filerne skal kopieres (mappen behøver \
            ikke eksistere i forvejen)",
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
        help="Navnet på den kolonne i csv-filen, der indeholder \
            fil-referencerne",
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


def copy_files(destination, files_to_copy) -> None:
    print("Copying...", flush=True)
    for key in files_to_copy:
        source_path = files_to_copy[key]
        shutil.copy(source_path, Path(destination, source_path.name))

def walk_source_dir(args, filenames) -> Tuple[Dict[str, str], List[str], List[str]]:
    files_to_copy: Dict[Path, Path] = {}
    detected_file_names: List[str] = []
    duplicate_file_names: List[str] = []

    for f in Path(args.source).glob("**/*"):
            if f.is_file() and f.name in filenames and f.name not in detected_file_names: 
                try:
                    files_to_copy[f] = Path(args.destination, f.name)
                    # print(f"{f.name} copied to destination", flush=True)
        #           copied_files.append(f)
                    detected_file_names.append(f.name)
                except Exception as e:
                    sys.exit(f"Unable to copy file to destination: {e}")
            else:
                duplicate_file_names.append(f.name)
                if args.delete:
                    f.unlink()
                    print((f"{f.name} deleted from original path"), flush=True)
    return files_to_copy, detected_file_names, duplicate_file_names

def print_duplicate_file_names(duplicate_file_names: List[str]):
    print("Files with the following file names where found more than ones: ")
    for name in duplicate_file_names:
        print(name)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
