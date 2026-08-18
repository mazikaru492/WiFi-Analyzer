import re

def remove_comments(source):
    # # コメントを安全に削除（文字列リテラル内を除く）
    lines = source.splitlines()
    cleaned_lines = []
    
    in_multiline = False
    
    for line in lines:
        # トリムと簡単な行判定
        stripped = line.strip()
        
        # docstring または コメント行の削除
        if stripped.startswith('"""') and stripped.endswith('"""') and len(stripped) > 3:
            continue
        if stripped.startswith("'''") and stripped.endswith("'''") and len(stripped) > 3:
            continue
            
        # # から始まるコメント行
        if stripped.startswith("#"):
            continue
            
        # 行末コメントの処理（文字列内 # に注意しながら単純分解）
        # 簡単な正規表現で文字列外の # を検出
        new_line = ""
        in_string = None
        i = 0
        while i < len(line):
            char = line[i]
            if char in ('"', "'"):
                if in_string is None:
                    in_string = char
                elif in_string == char:
                    in_string = None
                new_line += char
            elif char == '#' and in_string is None:
                break
            else:
                new_line += char
            i += 1
            
        if new_line.rstrip():
            cleaned_lines.append(new_line.rstrip())
        elif not line.strip():
            # 空白行は一部保持して見やすくする（連続する空白行は1行に圧縮）
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

    return "\n".join(cleaned_lines) + "\n"

with open("wifi_test.py", "r", encoding="utf-8") as f:
    code = f.read()

clean_code = remove_comments(code)

with open("wifi_test.py", "w", encoding="utf-8") as f:
    f.write(clean_code)

print("Comments removed successfully.")
