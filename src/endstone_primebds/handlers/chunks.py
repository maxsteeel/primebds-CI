from typing import TYPE_CHECKING

from endstone.event import ChunkLoadEvent, ChunkUnloadEvent
from endstone_primebds.utils.config_util import load_config

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

config = load_config()
#leak_fix = config["modules"]["server_optimizer"]["chunk_leak_fix"]
def handle_chunk_load(self: "PrimeBDS", ev: ChunkLoadEvent):
    return

def handle_chunk_unload(self: "PrimeBDS", ev: ChunkUnloadEvent):
    return