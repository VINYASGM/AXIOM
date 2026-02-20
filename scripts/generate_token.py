import hmac
import hashlib
import base64
import json
import time

def base64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')

def generate_jwt(secret, payload):
    header = {"alg": "HS256", "typ": "JWT"}
    
    encoded_header = base64url_encode(json.dumps(header).encode('utf-8'))
    encoded_payload = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    signature_input = encoded_header + b'.' + encoded_payload
    signature = hmac.new(secret.encode('utf-8'), signature_input, hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    
    return (signature_input + b'.' + encoded_signature).decode('utf-8')

secret = "dev-secret-change-in-production-use-openssl-rand-base64-32"
now = int(time.time())
exp = now + 31536000 # 1 year

payload = {
  "user_id": "e82bff92-9241-40c2-b705-62e9e748b9aa",
  "email": "developer@axiom.dev",
  "role": "developer",
  "sub": "e82bff92-9241-40c2-b705-62e9e748b9aa",
  "exp": exp,
  "iat": now
}

token = generate_jwt(secret, payload)
print(token)
