import struct
from io import BytesIO

from enum import Enum, IntEnum
from abc import ABC, abstractmethod

class MinecraftPacketIds(IntEnum):
    AddPlayer = 12
    TakeItemEntity = 17
    RemoveEntity = 14
    UpdateBlock = 21
    BlockEvent = 26
    OpenContainer = 46
    CloseContainer = 47
    InventoryContent = 49
    PlayerList = 63
    LevelSound = 123
    ItemRegistry = 162

class SoundType(Enum):
    ItemUseOn = 0
    Hit = 1
    Step = 2
    Fly = 3
    Jump = 4
    Break = 5
    Place = 6
    HeavyStep = 7
    Gallop = 8
    Fall = 9
    Ambient = 10
    AmbientBaby = 11
    AmbientInWater = 12
    Breathe = 13
    Death = 14
    DeathInWater = 15
    DeathToZombie = 16
    Hurt = 17
    HurtInWater = 18
    Mad = 19
    Boost = 20
    Bow = 21
    SquishBig = 22
    SquishSmall = 23
    FallBig = 24
    FallSmall = 25
    Splash = 26
    Fizz = 27
    Flap = 28
    Swim = 29
    Drink = 30
    Eat = 31
    Takeoff = 32
    Shake = 33
    Plop = 34
    Land = 35
    Saddle = 36
    Armor = 37
    MobArmorStandPlace = 38
    AddChest = 39
    Throw = 40
    Attack = 41
    AttackNodamage = 42
    AttackStrong = 43
    Warn = 44
    Shear = 45
    Milk = 46
    Thunder = 47
    Explode = 48
    Fire = 49
    Ignite = 50
    Fuse = 51
    Stare = 52
    Spawn = 53
    Shoot = 54
    BreakBlock = 55
    Launch = 56
    Blast = 57
    LargeBlast = 58
    Twinkle = 59
    Remedy = 60
    Unfect = 61
    Levelup = 62
    BowHit = 63
    BulletHit = 64
    ExtinguishFire = 65
    ItemFizz = 66
    ChestOpen = 67
    ChestClosed = 68
    ShulkerboxOpen = 69
    ShulkerboxClosed = 70
    EnderchestOpen = 71
    EnderchestClosed = 72
    PowerOn = 73
    PowerOff = 74
    Attach = 75
    Detach = 76
    Deny = 77
    Tripod = 78
    Pop = 79
    DropSlot = 80
    Note = 81
    Thorns = 82
    PistonIn = 83
    PistonOut = 84
    Portal = 85
    Water = 86
    LavaPop = 87
    Lava = 88
    Burp = 89
    BucketFillWater = 90
    BucketFillLava = 91
    BucketEmptyWater = 92
    BucketEmptyLava = 93
    ArmorEquipChain = 94
    ArmorEquipDiamond = 95
    ArmorEquipGeneric = 96
    ArmorEquipGold = 97
    ArmorEquipIron = 98
    ArmorEquipLeather = 99
    ArmorEquipElytra = 100
    Record13 = 101
    RecordCat = 102
    RecordBlocks = 103
    RecordChirp = 104
    RecordFar = 105
    RecordMall = 106
    RecordMellohi = 107
    RecordStal = 108
    RecordStrad = 109
    RecordWard = 110
    Record11 = 111
    RecordWait = 112
    StopRecord = 113
    Flop = 114
    ElderguardianCurse = 115
    MobWarning = 116
    MobWarningBaby = 117
    Teleport = 118
    ShulkerOpen = 119
    ShulkerClose = 120
    Haggle = 121
    HaggleYes = 122
    HaggleNo = 123
    HaggleIdle = 124
    ChorusGrow = 125
    ChorusDeath = 126
    Glass = 127
    PotionBrewed = 128
    CastSpell = 129
    PrepareAttack = 130
    PrepareSummon = 131
    PrepareWololo = 132
    Fang = 133
    Charge = 134
    CameraTakePicture = 135
    LeashknotPlace = 136
    LeashknotBreak = 137
    Growl = 138
    Whine = 139
    Pant = 140
    Purr = 141
    Purreow = 142
    DeathMinVolume = 143
    DeathMidVolume = 144
    ImitateBlaze = 145
    ImitateCaveSpider = 146
    ImitateCreeper = 147
    ImitateElderGuardian = 148
    ImitateEnderDragon = 149
    ImitateEnderman = 150
    ImitateEndermite = 151
    ImitateEvocationIllager = 152
    ImitateGhast = 153
    ImitateHusk = 154
    ImitateIllusionIllager = 155
    ImitateMagmaCube = 156
    ImitatePolarBear = 157
    ImitateShulker = 158
    ImitateSilverfish = 159
    ImitateSkeleton = 160
    ImitateSlime = 161
    ImitateSpider = 162
    ImitateStray = 163
    ImitateVex = 164
    ImitateVindicationIllager = 165
    ImitateWitch = 166
    ImitateWither = 167
    ImitateWitherSkeleton = 168
    ImitateWolf = 169
    ImitateZombie = 170
    ImitateZombiePigman = 171
    ImitateZombieVillager = 172
    BlockEndPortalFrameFill = 173
    BlockEndPortalSpawn = 174
    RandomAnvilUse = 175
    BottleDragonbreath = 176
    PortalTravel = 177
    ItemTridentHit = 178
    ItemTridentReturn = 179
    ItemTridentRiptide1 = 180
    ItemTridentRiptide2 = 181
    ItemTridentRiptide3 = 182
    ItemTridentThrow = 183
    ItemTridentThunder = 184
    ItemTridentHitGround = 185
    Default = 186
    FletchingTableUse = 187
    ElementConstructorOpen = 188
    IceBombHit = 189
    BalloonPop = 190
    LtReactionIceBomb = 191
    LtReactionBleach = 192
    LtReactionEPaste = 193
    LtReactionEPaste2 = 194
    LtReactionGlowStick = 195
    LtReactionGlowStick2 = 196
    LtReactionLuminol = 197
    LtReactionSalt = 198
    LtReactionFertilizer = 199
    LtReactionFireball = 200
    LtReactionMgSalt = 201
    LtReactionMiscFire = 202
    LtReactionFire = 203
    LtReactionMiscExplosion = 204
    LtReactionMiscMystical = 205
    LtReactionMiscMystical2 = 206
    LtReactionProduct = 207
    SparklerUse = 208
    GlowstickUse = 209
    SparklerActive = 210
    ConvertToDrowned = 211
    BucketFillFish = 212
    BucketEmptyFish = 213
    BubbleUp = 214
    BubbleDown = 215
    BubblePop = 216
    BubbleUpInside = 217
    BubbleDownInside = 218
    BabyHurt = 219
    BabyDeath = 220
    BabyStep = 221
    BabySpawn = 222
    Born = 223
    BlockTurtleEggBreak = 224
    BlockTurtleEggCrack = 225
    BlockTurtleEggHatch = 226
    TurtleLayEgg = 227
    BlockTurtleEggAttack = 228
    BeaconActivate = 229
    BeaconAmbient = 230
    BeaconDeactivate = 231
    BeaconPower = 232
    ConduitActivate = 233
    ConduitAmbient = 234
    ConduitAttack = 235
    ConduitDeactivate = 236
    ConduitShort = 237
    Swoop = 238
    BlockBambooSaplingPlace = 239
    PreSneeze = 240
    Sneeze = 241
    AmbientTame = 242
    Scared = 243
    BlockScaffoldingClimb = 244
    CrossbowLoadingStart = 245
    CrossbowLoadingMiddle = 246
    CrossbowLoadingEnd = 247
    CrossbowShoot = 248
    CrossbowQuickChargeStart = 249
    CrossbowQuickChargeMiddle = 250
    CrossbowQuickChargeEnd = 251
    AmbientAggressive = 252
    AmbientWorried = 253
    CantBreed = 254
    ShieldBlock = 255
    LecternBookPlace = 256
    GrindstoneUse = 257
    Bell = 258
    CampfireCrackle = 259
    Roar = 260
    Stun = 261
    SweetBerryBushHurt = 262
    SweetBerryBushPick = 263
    CartographyTableUse = 264
    StonecutterUse = 265
    ComposterEmpty = 266
    ComposterFill = 267
    ComposterFillLayer = 268
    ComposterReady = 269
    BarrelOpen = 270
    BarrelClose = 271
    RaidHorn = 272
    LoomUse = 273
    AmbientInRaid = 274
    UiCartographyTableUse = 275
    UiStonecutterUse = 276
    UiLoomUse = 277
    SmokerUse = 278
    BlastFurnaceUse = 279
    SmithingTableUse = 280
    Screech = 281
    Sleep = 282
    FurnaceUse = 283
    MooshroomConvert = 284
    MilkSuspiciously = 285
    Celebrate = 286
    JumpPrevent = 287
    AmbientPollinate = 288
    BeehiveDrip = 289
    BeehiveEnter = 290
    BeehiveExit = 291
    BeehiveWork = 292
    BeehiveShear = 293
    HoneybottleDrink = 294
    AmbientCave = 295
    Retreat = 296
    ConvertToZombified = 297
    Admire = 298
    StepLava = 299
    Tempt = 300
    Panic = 301
    Angry = 302
    AmbientWarpedForest = 303
    AmbientSoulsandValley = 304
    AmbientNetherWastes = 305
    AmbientBasaltDeltas = 306
    AmbientCrimsonForest = 307
    RespawnAnchorCharge = 308
    RespawnAnchorDeplete = 309
    RespawnAnchorSetSpawn = 310
    RespawnAnchorAmbient = 311
    SoulEscapeQuiet = 312
    SoulEscapeLoud = 313
    RecordPigstep = 314
    LinkCompassToLodestone = 315
    UseSmithingTable = 316
    EquipNetherite = 317
    AmbientLoopWarpedForest = 318
    AmbientLoopSoulsandValley = 319
    AmbientLoopNetherWastes = 320
    AmbientLoopBasaltDeltas = 321
    AmbientLoopCrimsonForest = 322
    AmbientAdditionWarpedForest = 323
    AmbientAdditionSoulsandValley = 324
    AmbientAdditionNetherWastes = 325
    AmbientAdditionBasaltDeltas = 326
    AmbientAdditionCrimsonForest = 327
    SculkSensorPowerOn = 328
    SculkSensorPowerOff = 329
    BucketFillPowderSnow = 330
    BucketEmptyPowderSnow = 331
    PointedDripstoneCauldronDripLava = 332
    PointedDripstoneCauldronDripWater = 333
    PointedDripstoneDripLava = 334
    PointedDripstoneDripWater = 335
    CaveVinesPickBerries = 336
    BigDripleafTiltDown = 337
    BigDripleafTiltUp = 338
    CopperWaxOn = 339
    CopperWaxOff = 340
    Scrape = 341
    PlayerHurtDrown = 342
    PlayerHurtOnFire = 343
    PlayerHurtFreeze = 344
    UseSpyglass = 345
    StopUsingSpyglass = 346
    AmethystBlockChime = 347
    AmbientScreamer = 348
    HurtScreamer = 349
    DeathScreamer = 350
    MilkScreamer = 351
    JumpToBlock = 352
    PreRam = 353
    PreRamScreamer = 354
    RamImpact = 355
    RamImpactScreamer = 356
    SquidInkSquirt = 357
    GlowSquidInkSquirt = 358
    ConvertToStray = 359
    CakeAddCandle = 360
    ExtinguishCandle = 361
    AmbientCandle = 362
    BlockClick = 363
    BlockClickFail = 364
    SculkCatalystBloom = 365
    SculkShriekerShriek = 366
    WardenNearbyClose = 367
    WardenNearbyCloser = 368
    WardenNearbyClosest = 369
    WardenSlightlyAngry = 370
    RecordOtherside = 371
    Tongue = 372
    CrackIronGolem = 373
    RepairIronGolem = 374
    Listening = 375
    Heartbeat = 376
    HornBreak = 377
    SculkPlace = 378
    SculkSpread = 379
    SculkCharge = 380
    SculkSensorPlace = 381
    SculkShriekerPlace = 382
    GoatCall0 = 383
    GoatCall1 = 384
    GoatCall2 = 385
    GoatCall3 = 386
    GoatCall4 = 387
    GoatCall5 = 388
    GoatCall6 = 389
    GoatCall7 = 390
    GoatCall8 = 391
    GoatCall9 = 392
    GoatHarmony0 = 393
    GoatHarmony1 = 394
    GoatHarmony2 = 395
    GoatHarmony3 = 396
    GoatHarmony4 = 397
    GoatHarmony5 = 398
    GoatHarmony6 = 399
    GoatHarmony7 = 400
    GoatHarmony8 = 401
    GoatHarmony9 = 402
    GoatMelody0 = 403
    GoatMelody1 = 404
    GoatMelody2 = 405
    GoatMelody3 = 406
    GoatMelody4 = 407
    GoatMelody5 = 408
    GoatMelody6 = 409
    GoatMelody7 = 410
    GoatMelody8 = 411
    GoatMelody9 = 412
    GoatBass0 = 413
    GoatBass1 = 414
    GoatBass2 = 415
    GoatBass3 = 416
    GoatBass4 = 417
    GoatBass5 = 418
    GoatBass6 = 419
    GoatBass7 = 420
    GoatBass8 = 421
    GoatBass9 = 422
    ImitateWarden = 426
    ListeningAngry = 427
    ItemGiven = 428
    ItemTaken = 429
    Disappeared = 430
    Reappeared = 431
    MilkDrink = 432
    FrogspawnHatched = 433
    LaySpawn = 434
    FrogspawnBreak = 435
    SonicBoom = 436
    SonicCharge = 437
    ItemThrown = 438
    Record5 = 439
    ConvertToFrog = 440
    RecordPlaying = 441
    EnchantingTableUse = 442
    StepSand = 443
    DashReady = 444
    BundleDropContents = 445
    BundleInsert = 446
    BundleRemoveOne = 447
    PressurePlateClickOff = 448
    PressurePlateClickOn = 449
    ButtonClickOff = 450
    ButtonClickOn = 451
    DoorOpen = 452
    DoorClose = 453
    TrapdoorOpen = 454
    TrapdoorClose = 455
    FenceGateOpen = 456
    FenceGateClose = 457
    Insert = 458
    Pickup = 459
    InsertEnchanted = 460
    PickupEnchanted = 461
    Brush = 462
    BrushCompleted = 463
    ShatterDecoratedPot = 464
    BreakDecoratedPod = 465
    SnifferEggCrack = 466
    SnifferEggHatched = 467
    WaxedSignInteractFail = 468
    RecordRelic = 469
    Bump = 470
    PumpkinCarve = 471
    ConvertHuskToZombie = 472
    PigDeath = 473
    HoglinZombified = 474
    AmbientUnderwaterEnter = 475
    AmbientUnderwaterExit = 476
    BottleFill = 477
    BottleEmpty = 478
    CrafterCraft = 479
    CrafterFailed = 480
    BlockDecoratedPotInsert = 481
    BlockDecoratedPotInsertFail = 482
    CrafterDisableSlot = 483
    SmithingTransform = 484
    TrailRuinsDigestComplete = 485
    TrailRuinsDigestStart = 486
    CrafterCrafted = 487
    CrafterFailedCraft = 488
    TrialSpawnerSpawn = 489
    TrialSpawnerAboutToSpawn = 490
    TrialSpawnerSpawned = 491
    TrialSpawnerDetectedPlayer = 492
    TrialSpawnerEjectItem = 493
    OminousTrialSpawnerDetectedPlayer = 494
    OminousTrialSpawnerAboutToSpawn = 495
    OminousTrialSpawnerSpawned = 496
    OminousTrialSpawnerEjectItem = 497
    BreezeCharge = 498
    BreezeShoot = 499
    BreezeInhale = 500
    BreezeExhale = 501
    BreezeSlide = 502
    BreezeDeflect = 503
    BreezeLand = 504
    BreezeJump = 505
    WindChargeThrow = 506
    WindChargeHit = 507
    WindChargeExplosion = 508
    WindChargeTravel = 509
    WindBlast = 510
    VaultDeactivate = 511
    VaultActivate = 512
    VaultInsertItem = 513
    VaultEjectItem = 514
    VaultAmbient = 515
    VaultOpen = 516
    VaultClose = 517
    VaultLock = 518
    VaultUnlock = 519
    VaultFail = 520
    OminousVaultActivate = 521
    OminousVaultAmbient = 522
    OminousVaultOpen = 523
    OminousVaultClose = 524
    OminousVaultLock = 525
    OminousVaultUnlock = 526
    OminousVaultFail = 527
    ItemPickupToBundle = 528
    MusicDiscPlay = 529
    MusicDiscStop = 530
    BlockSuspiciousGravelStep = 531
    BlockSuspiciousGravelBreak = 532
    BlockSuspiciousGravelPlace = 533
    BlockSuspiciousGravelHit = 534
    BlockSuspiciousGravelFall = 535
    BlockSuspiciousSandStep = 536
    BlockSuspiciousSandBreak = 537
    BlockSuspiciousSandPlace = 538
    BlockSuspiciousSandHit = 539
    BlockSuspiciousSandFall = 540
    MusicDiscLoop = 541
    MusicDiscSearchStop = 542
    MusicDiscSearchVolume = 543
    VaultUnlockSound = 544
    VaultLockedSound = 545
    VaultCloseSound = 546
    VaultOpenSound = 547
    VaultAmbientSound = 548
    VaultFailSound = 549
    VaultActivateSound = 550
    VaultDeactivateSound = 551
    VaultEjectItemSound = 552
    VaultInsertItemSound = 553
    VaultLockSound = 554
    VaultUnlockSoundEffect = 555
    VaultFailSoundEffect = 556
    VaultCloseSoundEffect = 557
    VaultOpenSoundEffect = 558
    VaultAmbientSoundEffect = 559
    VaultActivateSoundEffect = 560
    VaultDeactivateSoundEffect = 561
    VaultEjectItemSoundEffect = 562

class DeviceOS(IntEnum):
    Undefined = 0
    Android = 1
    IOS = 2
    OSX = 3
    FireOS = 4
    GearVR = 5
    Hololens = 6
    Win10 = 7
    Win32 = 8
    Dedicated = 9
    TVOS = 10
    Orbis = 11
    NintendoSwitch = 12
    Xbox = 13
    WindowsPhone = 14
    Linux = 15

class Packet(ABC):
    @abstractmethod
    def get_packet_id(self) -> 'MinecraftPacketIds':
        pass

    @abstractmethod
    def serialize(self) -> bytes:
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        pass

class BufferWriter:
    def __init__(self):
        self.buffer = BytesIO()

    def write_byte(self, value: int):
        self.buffer.write(struct.pack("b", value))

    def write_ubyte(self, value: int):
        self.buffer.write(struct.pack("B", value))

    def write_short(self, value: int):
        self.buffer.write(struct.pack(">h", value))

    def write_ushort(self, value: int):
        self.buffer.write(struct.pack(">H", value))

    def write_int(self, value: int):
        self.buffer.write(struct.pack(">i", value))

    def write_uint(self, value: int):
        self.buffer.write(struct.pack(">I", value))

    def write_long(self, value: int):
        self.buffer.write(struct.pack(">q", value))

    def write_ulong(self, value: int):
        self.buffer.write(struct.pack(">Q", value))

    def write_float(self, value: float):
        self.buffer.write(struct.pack(">f", value))

    def write_double(self, value: float):
        self.buffer.write(struct.pack(">d", value))

    def write_float3(self, x: float, y: float, z: float):
        self.buffer.write(struct.pack("<fff", x, y, z))

    def write_bool(self, value: bool):
        self.buffer.write(struct.pack("<?", value))

    def write_li64(self, value: int):
        self.buffer.write(struct.pack("<q", value))

    def write_zigzag64(self, value: int):
        encoded = (value << 1) ^ (value >> 63)
        self.buffer.write(struct.pack("<Q", encoded))

    def write_zigzag64_varint(self, value: int):
        encoded = (value << 1) ^ (value >> 63)
        self.write_varlong(encoded)

    def write_varint(self, value: int):
        v = value & 0xFFFFFFFF
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                self.write_ubyte(b | 0x80)
            else:
                self.write_ubyte(b)
                break

    def write_varlong(self, value: int):
        v = value & 0xFFFFFFFFFFFFFFFF
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                self.write_ubyte(b | 0x80)
            else:
                self.write_ubyte(b)
                break

    def write_string(self, value: str):
        encoded = value.encode("utf-8")
        self.write_varint(len(encoded))
        self.buffer.write(encoded)

    def getvalue(self) -> bytes:
        return self.buffer.getvalue()

class BufferReader:
    def __init__(self, data: bytes):
        self.buffer = BytesIO(data)

    def read_byte(self) -> int:
        return struct.unpack("b", self.buffer.read(1))[0]

    def read_ubyte(self) -> int:
        return struct.unpack("B", self.buffer.read(1))[0]

    def read_short(self) -> int:
        return struct.unpack(">h", self.buffer.read(2))[0]

    def read_ushort(self) -> int:
        return struct.unpack(">H", self.buffer.read(2))[0]

    def read_int(self) -> int:
        return struct.unpack(">i", self.buffer.read(4))[0]

    def read_uint(self) -> int:
        return struct.unpack(">I", self.buffer.read(4))[0]

    def read_long(self) -> int:
        return struct.unpack(">q", self.buffer.read(8))[0]

    def read_ulong(self) -> int:
        return struct.unpack(">Q", self.buffer.read(8))[0]

    def read_float(self) -> float:
        return struct.unpack(">f", self.buffer.read(4))[0]

    def read_double(self) -> float:
        return struct.unpack(">d", self.buffer.read(8))[0]
    
    def read_float3(self) -> tuple[float, float, float]:
        return struct.unpack("<fff", self.buffer.read(12))

    def read_bool(self) -> bool:
        return struct.unpack("<?", self.buffer.read(1))[0]

    def read_li64(self) -> int:
        return struct.unpack("<q", self.buffer.read(8))[0]
    
    def read_zigzag64(self) -> int:
        raw_bytes = self.buffer.read(8)
        if len(raw_bytes) < 8:
            raise EOFError("Not enough bytes to read ZigZag64")
        encoded = struct.unpack("<Q", raw_bytes)[0]
        return (encoded >> 1) ^ -(encoded & 1)
    
    def read_zigzag64_varint(self) -> int:
        encoded = self.read_varlong()      
        return (encoded >> 1) ^ -(encoded & 1) 

    def read_varint(self) -> int:
        shift = 0
        result = 0
        while True:
            b = self.read_ubyte()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift >= 32:
                raise ValueError("VarInt too big")
        return result

    def read_varlong(self) -> int:
        shift = 0
        result = 0
        while True:
            b = self.read_ubyte()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift >= 64:
                raise ValueError("VarLong too big")
        return result

    def read_string(self) -> str:
        length = self.read_varint()
        return self.buffer.read(length).decode("utf-8")

class PacketDebugger:

    @staticmethod
    def debug(packet_bytes: bytes):
        if not isinstance(packet_bytes, (bytes, bytearray)):
            raise TypeError("debug expects bytes or bytearray")

        def to_hex_line(data, start):
            hex_str = ' '.join(f'{b:02X}' for b in data)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
            return f"{start:04X}: {hex_str:<48}  {ascii_str}"

        length = len(packet_bytes)
        print(f"Packet length: {length} bytes")
        print("-" * 60)
        for i in range(0, length, 16):
            line = packet_bytes[i:i+16]
            print(to_hex_line(line, i))
        print("-" * 60)

        if length == 0:
            print("Empty packet")
            return
        if length < 2:
            print("Packet is suspiciously short")
        if length >= 3 and packet_bytes[-3:] == b'\x00\x00\x00':
            print("Packet ends with multiple null bytes")
        print("Debug complete\n")