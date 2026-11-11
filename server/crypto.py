from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(f"This is the key: {key}")
cipher = Fernet(key)
print(f"This is cipher: {cipher}")
word = b"you shouldve seen that"
print(f"Word: {word}")
encrypted = cipher.encrypt(word)
print(f"This is the word encrypted: {encrypted}")
decrypted = cipher.decrypt(encrypted)
print(f"This is the word decrypted: {decrypted.decode()}")
