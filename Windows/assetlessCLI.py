import os
import shutil

def replicate_structure_with_a(source_dir, dest_dir):
    for root, dirs, files in os.walk(source_dir):
        # Compute the relative path from source
        rel_path = os.path.relpath(root, source_dir)
        # Create corresponding directory in destination
        dest_path = os.path.join(dest_dir, rel_path)
        os.makedirs(dest_path, exist_ok=True)

        for file in files:
            # Construct the full file path in destination
            _, ext = os.path.splitext(file)
            dest_file_path = os.path.join(dest_path, file)

            # Write "A" into each new file
            try:
                with open(dest_file_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                print(f"Error creating file {dest_file_path}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: assetlessBuildingCLI [source folder] [destination folder]")
        exit()
    source_folder = sys.argv[1]
    if not source_folder or not os.path.exists(source_folder):
        print("No source folder selected.")
        exit()
    print(source_folder)
    dest_folder = sys.argv[2]
    if not dest_folder:
        print("No destination folder selected.")
        exit()
    print(dest_folder)

    replicate_structure_with_a(source_folder, dest_folder)
    print("Replication complete.")
