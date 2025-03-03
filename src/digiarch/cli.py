from acacore.__version__ import __version__ as __acacore_version__
from click import group
from click import version_option
from PIL import Image

from .__version__ import __version__
from .commands.completions import cmd_completions
from .commands.edit.edit import grp_edit
from .commands.extract.extract import cmd_extract
from .commands.finalize.finalize import grp_finalize
from .commands.help import cmd_help
from .commands.identify import grp_identify
from .commands.info import cmd_info
from .commands.init import cmd_init
from .commands.log import cmd_log
from .commands.manual import grp_manual
from .commands.search import grp_search
from .commands.upgrade import cmd_upgrade

Image.MAX_IMAGE_PIXELS = int(50e3**2)


@group("digiarch", no_args_is_help=True)
@version_option(__version__, message=f"%(prog)s, version %(version)s\nacacore, version {__acacore_version__}")
def app():
    """Indentify files and process AVID archives."""


# noinspection DuplicatedCode
app.add_command(cmd_init, cmd_init.name)
app.add_command(grp_identify, grp_identify.name)
app.add_command(cmd_extract, cmd_extract.name)
app.add_command(grp_edit, grp_edit.name)
app.add_command(grp_manual, grp_manual.name)
app.add_command(grp_finalize, grp_finalize.name)
app.add_command(grp_search, grp_search.name)
app.add_command(cmd_info, cmd_info.name)
app.add_command(cmd_log, cmd_log.name)
app.add_command(cmd_upgrade, cmd_upgrade.name)
app.add_command(cmd_help, cmd_help.name)
app.add_command(cmd_completions, cmd_completions.name)

app.list_commands = lambda _ctx: list(app.commands)
