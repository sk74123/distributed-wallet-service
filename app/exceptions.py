class WalletNotFoundError(Exception):
    def __init__(self, wallet_id: int):
        self.wallet_id = wallet_id
        super().__init__(f"Wallet {wallet_id} not found")


class InsufficientBalanceError(Exception):
    def __init__(self, wallet_id: int, required: float, available: float):
        self.wallet_id = wallet_id
        self.required = required
        self.available = available
        super().__init__(
            f"Wallet {wallet_id} has insufficient balance. "
            f"Required: {required}, Available: {available}"
        )


class TransferNotFoundError(Exception):
    def __init__(self, transfer_id: str):
        self.transfer_id = transfer_id
        super().__init__(f"Transfer {transfer_id} not found")


class DuplicateTransferError(Exception):
    def __init__(self, transfer_id: str):
        self.transfer_id = transfer_id
        super().__init__(f"Transfer {transfer_id} already exists")


class InvalidTransferError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid transfer: {reason}")
