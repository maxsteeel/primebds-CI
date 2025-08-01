def get_runtime_id(self, block_id: str) -> int:
    block_data = self.server.create_block_data(block_id)
    return block_data.runtime_id