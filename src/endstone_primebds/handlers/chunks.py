from typing import TYPE_CHECKING

from endstone.event import ChunkLoadEvent, ChunkUnloadEvent
from endstone_primebds.utils.config_util import load_config

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

config = load_config()
chunks = config["modules"]["server_optimizer"]["chunk_loading"]
def handle_chunk_load(self: "PrimeBDS", ev: ChunkLoadEvent):
    if chunks:
        chunk_coords = (ev.chunk.x, ev.chunk.z)
        if chunk_coords in self.sent_chunks:
            ev.is_cancelled = True
            return

        self.sent_chunks.add(chunk_coords)

        MAX_TRACKED_CHUNKS = 200
        if len(self.sent_chunks) > MAX_TRACKED_CHUNKS:
            self.sent_chunks = set(list(self.sent_chunks)[-MAX_TRACKED_CHUNKS:])

def handle_chunk_unload(self: "PrimeBDS", ev: ChunkUnloadEvent):
    if chunks:
        chunk_coords = (ev.chunk.x, ev.chunk.z)
        self.sent_chunks.discard(chunk_coords)