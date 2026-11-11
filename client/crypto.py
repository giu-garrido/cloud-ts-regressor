from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)
word = b"you shouldve seen that"
encrypted = cipher.encrypt(word)
decrypted = cipher.decrypt(encrypted)
print(f"This is the word decrypted: {decrypted.decode()}")