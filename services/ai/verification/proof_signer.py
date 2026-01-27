"""
Proof Signer for Proof-Carrying Code

Ed25519 cryptographic signing and verification of verification proofs.
"""
import hashlib
import json
import time
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Proof signing disabled.")


@dataclass
class SigningKey:
    """Ed25519 signing key pair."""
    private_key: Any  # Ed25519PrivateKey
    public_key: Any   # Ed25519PublicKey
    key_id: str
    created_at: float


class ProofSigner:
    """
    Ed25519-based proof signer for verification proofs.
    
    Provides:
    - Key pair generation
    - Proof signing
    - Signature verification
    - Key serialization/deserialization
    """
    
    def __init__(self, key_directory: Optional[str] = None):
        self.key_directory = key_directory or os.path.join(
            os.path.dirname(__file__), ".keys"
        )
        self.current_key: Optional[SigningKey] = None
        
        # Ensure key directory exists
        os.makedirs(self.key_directory, exist_ok=True)
    
    def generate_key_pair(self, key_id: Optional[str] = None) -> SigningKey:
        """
        Generate a new Ed25519 key pair.
        
        Args:
            key_id: Optional identifier for the key
            
        Returns:
            SigningKey with private and public keys
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        key_id = key_id or hashlib.sha256(
            public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).hexdigest()[:16]
        
        return SigningKey(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
            created_at=time.time()
        )
    
    def load_or_create_key(self, key_name: str = "axiom_signer") -> SigningKey:
        """
        Load existing key or create new one.
        
        Args:
            key_name: Name of the key file (without extension)
            
        Returns:
            SigningKey
        """
        private_key_path = os.path.join(self.key_directory, f"{key_name}.pem")
        
        if os.path.exists(private_key_path):
            return self.load_key(key_name)
        else:
            key = self.generate_key_pair(key_name)
            self.save_key(key, key_name)
            return key
    
    def save_key(self, key: SigningKey, key_name: str) -> None:
        """Save key pair to files."""
        if not CRYPTO_AVAILABLE:
            return
        
        private_key_path = os.path.join(self.key_directory, f"{key_name}.pem")
        public_key_path = os.path.join(self.key_directory, f"{key_name}.pub")
        
        # Save private key (PEM format, unencrypted for dev)
        private_pem = key.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(private_key_path, 'wb') as f:
            f.write(private_pem)
        
        # Save public key
        public_pem = key.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(public_key_path, 'wb') as f:
            f.write(public_pem)
    
    def load_key(self, key_name: str) -> SigningKey:
        """Load key pair from files."""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        private_key_path = os.path.join(self.key_directory, f"{key_name}.pem")
        
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
        
        public_key = private_key.public_key()
        
        key_id = hashlib.sha256(
            public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).hexdigest()[:16]
        
        return SigningKey(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
            created_at=os.path.getmtime(private_key_path)
        )
    
    def sign_proof(
        self,
        proof_data: Dict[str, Any],
        key: Optional[SigningKey] = None
    ) -> Tuple[bytes, str]:
        """
        Sign a verification proof.
        
        Args:
            proof_data: Dictionary containing proof data to sign
            key: Optional signing key (uses current key if not provided)
            
        Returns:
            Tuple of (signature_bytes, signer_id)
        """
        if not CRYPTO_AVAILABLE:
            return b"", "unsigned"
        
        signing_key = key or self.current_key
        if signing_key is None:
            signing_key = self.load_or_create_key()
            self.current_key = signing_key
        
        # Create canonical representation for signing
        canonical = self._canonicalize(proof_data)
        
        # Sign
        signature = signing_key.private_key.sign(canonical)
        
        return signature, signing_key.key_id
    
    def verify_signature(
        self,
        proof_data: Dict[str, Any],
        signature: bytes,
        public_key_bytes: Optional[bytes] = None,
        key: Optional[SigningKey] = None
    ) -> bool:
        """
        Verify a proof signature.
        
        Args:
            proof_data: Dictionary containing proof data that was signed
            signature: The signature to verify
            public_key_bytes: Raw public key bytes (optional)
            key: SigningKey containing public key (optional)
            
        Returns:
            True if signature is valid
        """
        if not CRYPTO_AVAILABLE:
            return False
        
        try:
            if public_key_bytes:
                public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            elif key:
                public_key = key.public_key
            elif self.current_key:
                public_key = self.current_key.public_key
            else:
                return False
            
            canonical = self._canonicalize(proof_data)
            public_key.verify(signature, canonical)
            return True
            
        except InvalidSignature:
            return False
        except Exception:
            return False
    
    def get_public_key_bytes(self, key: Optional[SigningKey] = None) -> bytes:
        """Get raw public key bytes for distribution."""
        if not CRYPTO_AVAILABLE:
            return b""
        
        k = key or self.current_key
        if k is None:
            return b""
        
        return k.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def get_public_key_pem(self, key: Optional[SigningKey] = None) -> str:
        """Get public key in PEM format."""
        if not CRYPTO_AVAILABLE:
            return ""
        
        k = key or self.current_key
        if k is None:
            return ""
        
        return k.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def _canonicalize(self, data: Dict[str, Any]) -> bytes:
        """
        Create canonical byte representation for signing.
        
        Uses JSON with sorted keys for deterministic output.
        """
        # Remove signature-related fields to avoid circular dependency
        signable = {k: v for k, v in data.items() if k not in ['signature', 'signer_id']}
        
        return json.dumps(
            signable,
            sort_keys=True,
            separators=(',', ':'),
            default=str
        ).encode('utf-8')


# Singleton instance
_proof_signer: Optional[ProofSigner] = None


def get_proof_signer() -> ProofSigner:
    """Get or create proof signer singleton."""
    global _proof_signer
    if _proof_signer is None:
        _proof_signer = ProofSigner()
    return _proof_signer
