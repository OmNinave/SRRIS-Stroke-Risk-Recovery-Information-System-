import os

replace_str = "http://localhost:8000/api"
new_str = "/api"

frontend_dir = r"a:\Coding Space\Workspace\SRRIS\frontend\src"

for root, _, files in os.walk(frontend_dir):
    for filename in files:
        if filename.endswith(".tsx") or filename.endswith(".ts"):
            path = os.path.join(root, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if replace_str in content:
                content = content.replace(replace_str, new_str)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Replaced in: {path}")

print("Replacement Complete.")
