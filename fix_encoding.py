import os

def convert_encoding(filename, src_enc, dest_enc='utf-8'):
    try:
        with open(filename, 'r', encoding=src_enc) as f:
            content = f.read()
        with open(filename, 'w', encoding=dest_enc) as f:
            f.write(content)
        print(f"Converted {filename} from {src_enc} to {dest_enc}")
    except Exception as e:
        print(f"Failed to convert {filename}: {e}")

# The error complained about utf-16le
convert_encoding('bot.py', 'utf-16le')
