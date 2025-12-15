
import os
import zipfile

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            # Create a relative path for the file to keep the directory structure
            # inside the zip file.
            relative_path = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
            ziph.write(os.path.join(root, file), arcname=relative_path)

if __name__ == '__main__':
    zipf = zipfile.ZipFile('project.zip', 'w', zipfile.ZIP_DEFLATED)
    # Exclude the virtual environment, previous tar file, and the zip file itself.
    exclusions = ['.venv', 'project.tar.gz', 'project.zip', '.git', '__pycache__']
    for root, dirs, files in os.walk('.'):
        # filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclusions]
        for file in files:
            if file not in exclusions:
                zipf.write(os.path.join(root, file))
    zipf.close()
