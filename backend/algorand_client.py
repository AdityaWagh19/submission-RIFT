"""
Algorand client singleton for TestNet interaction.
"""
from algosdk.v2client import algod
from config import settings
import logging

logger = logging.getLogger(__name__)


class AlgorandClient:
    """Singleton Algorand client for TestNet operations."""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlgorandClient, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance
    
    def _initialize_client(self):
        """Initialize the Algorand algod client."""
        try:
            self._client = algod.AlgodClient(
                algod_token=settings.algorand_algod_token,
                algod_address=settings.algorand_algod_address
            )
            # Test connection
            status = self._client.status()
            logger.info(f"Connected to Algorand TestNet. Current round: {status.get('last-round')}")
        except Exception as e:
            logger.error(f"Failed to initialize Algorand client: {e}")
            raise
    
    @property
    def client(self) -> algod.AlgodClient:
        """Get the algod client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def get_suggested_params(self):
        """Fetch suggested transaction parameters from TestNet."""
        try:
            return self._client.suggested_params()
        except Exception as e:
            logger.error(f"Error fetching suggested params: {e}")
            raise
    
    def send_raw_transaction(self, signed_txn: bytes) -> str:
        """
        Submit a signed transaction to TestNet.
        
        Args:
            signed_txn: Base64-decoded signed transaction bytes
            
        Returns:
            Transaction ID
        """
        try:
            tx_id = self._client.send_raw_transaction(signed_txn)
            logger.info(f"Transaction submitted successfully: {tx_id}")
            return tx_id
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            raise


# Global client instance
algorand_client = AlgorandClient()
