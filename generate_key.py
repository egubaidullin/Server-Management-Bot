import base64
import os

def generate_url_safe_base64_key(length=32):
    # Generate a random byte string of the specified length
    random_bytes = os.urandom(length)

    # Encode the byte string using URL-safe base64 encoding
    url_safe_base64_key = base64.urlsafe_b64encode(random_bytes)

    # Decode the base64-encoded bytes to a string
    url_safe_base64_key_str = url_safe_base64_key.decode('utf-8')

    return url_safe_base64_key_str

# Generate a 32-byte URL-safe base64-encoded key
key = generate_url_safe_base64_key()
print(key)
