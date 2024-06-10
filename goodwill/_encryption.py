from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from urllib.parse import quote


def _encrypt_model_value(value:str):
    encrypt_secret_key_url = "6696D2E6F042FEC4D6E3F32AD541143B"  

    # Prepare the key and initialization vector (IV)
    m = encrypt_secret_key_url.encode('utf-8')
    ae = b'0000000000000000'
    
    # Create the AES cipher in CBC mode with the provided key and IV
    cipher = AES.new(m, AES.MODE_CBC, iv=ae)
    
    # Encrypt the plaintext P, padded to the block size
    padded_P = pad(value.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_P)
    
    # Encode the encrypted bytes in base64 to get a string
    encrypted_base64 = base64.b64encode(encrypted_bytes).decode('utf-8')
    
    # URL-encode the base64 string
    encrypted_url_encoded = quote(encrypted_base64)
    
    return encrypted_url_encoded