from pathlib import Path
from typing import ClassVar
from typing import Generator

from tnefparse import TNEF

from digiarch.extract.extractors.base import ExtractorBase


class TNEFExtractor(ExtractorBase):
    tool_names: ClassVar[list[str]] = [
        "tnefparse",  # kept for backwards compatibility
        "tnef",
    ]

    def extract(self) -> Generator[Path, None, None]:
        extract_folder: Path = self.extract_folder
        extract_folder.mkdir(parents=True, exist_ok=True)

        with self.file.get_absolute_path().open("rb") as fh:
            tnef = TNEF(fh.read())

            for attachment in tnef.attachments:
                path = extract_folder.joinpath("attachments", attachment.long_filename() or attachment.name)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as oh:
                    oh.write(attachment.data)
                    yield path

            if tnef.htmlbody:
                (body_path := extract_folder.joinpath(f"{self.file.stem}_body.html")).write_text(tnef.htmlbody)
                yield body_path
            elif tnef.rtfbody:
                (body_path := extract_folder.joinpath(f"{self.file.stem}_body.rtf")).write_bytes(tnef.rtfbody)
                yield body_path
            elif tnef.body and isinstance(tnef.body, bytes):
                (body_path := extract_folder.joinpath(f"{self.file.stem}_body.txt")).write_bytes(tnef.body)
                yield body_path
            elif tnef.body:
                (body_path := extract_folder.joinpath(f"{self.file.stem}_body.txt")).write_text(tnef.body)
                yield body_path
