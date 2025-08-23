from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, Packet, BufferWriter, BufferReader

class LevelSoundEventPacket(Packet):
    def __init__(self,
                 sound_type: int = 0,
                 x: float = 0.0,
                 y: float = 0.0,
                 z: float = 0.0,
                 extra_data: int = 0,
                 entity_type: str = "",
                 baby_mob: bool = False,
                 global_sound: bool = False,
                 actor_unique_id: int = 0):
        self.sound_type = sound_type
        self.x = x
        self.y = y
        self.z = z
        self.extra_data = extra_data
        self.entity_type = entity_type
        self.baby_mob = baby_mob
        self.global_sound = global_sound
        self.actor_unique_id = actor_unique_id

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.LevelSound

    def serialize(self) -> bytes:
        w = BufferWriter()
        w.write_varint(self.sound_type)
        w.write_float3(self.x, self.y, self.z)
        w.write_varint(self.extra_data)
        w.write_string(self.entity_type)
        w.write_bool(self.baby_mob)
        w.write_bool(self.global_sound)
        w.write_li64(self.actor_unique_id)
        return w.getvalue()

    def deserialize(self, data: bytes) -> None:
        r = BufferReader(data)
        self.sound_type = r.read_varint()
        self.x, self.y, self.z = r.read_float3()
        self.extra_data = r.read_varint()
        self.entity_type = r.read_string()
        self.baby_mob = r.read_bool()
        self.global_sound = r.read_bool()
        self.actor_unique_id = r.read_li64()
