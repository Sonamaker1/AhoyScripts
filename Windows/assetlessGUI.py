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
    import PyQt6 as qt
    import sys
    from PyQt6.QtWidgets import QFileDialog, QApplication, QMainWindow
    app = QApplication(sys.argv)
    main = QMainWindow()
    main.show()
    # Open dialog to select source and destination folders
    #root = tk.Tk()
    #root.withdraw()  # Hide the main window

    print("Select the source folder...")
    source_folder = QFileDialog.getExistingDirectory(
		caption="Select the source folder",
		directory="",
		options=QFileDialog.Option.DontUseNativeDialog,
	)
	
    if not source_folder:
        print("No source folder selected.")
        exit()
    print(source_folder)
    print("Select the destination folder...")
    dest_folder = QFileDialog.getExistingDirectory(
		caption="Select the destination folder",
		directory="",
		options=QFileDialog.Option.DontUseNativeDialog,
	)
    if not dest_folder:
        print("No destination folder selected.")
        exit()

    replicate_structure_with_a(source_folder, dest_folder)
    print("Replication complete.")
