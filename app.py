from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime
import zipfile
import io
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_creation_time(file_path):
    """Get file creation time (or modification time as fallback)"""
    try:
        # Try to get creation time first
        return os.path.getctime(file_path)
    except:
        # Fallback to modification time
        return os.path.getmtime(file_path)

def generate_naming_sequence(count, folder_name):
    """Generate a sequence of names based on the number of images and folder name"""
    if count < 1:
        return []
    
    # First image is "1 intro [folder_name]"
    # Rest are just numbered "[number] [folder_name]"
    sequence = [f"1 intro {folder_name}"]
    
    # Add remaining numbered items
    for i in range(2, count + 1):
        sequence.append(f"{i} {folder_name}")
    
    return sequence

def process_images(folder_path, folder_name=None):
    """Process images in the given folder, renaming them based on creation time"""
    # Get all image files
    files = [f for f in os.listdir(folder_path) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) 
             and os.path.isfile(os.path.join(folder_path, f))]
    
    # Get creation time for each file
    files_with_time = [(file, get_creation_time(os.path.join(folder_path, file))) 
                       for file in files]
    
    # Sort files by creation time
    files_with_time.sort(key=lambda x: x[1])
    
    # If folder_name is not provided, use the name of the folder
    if not folder_name:
        folder_name = os.path.basename(folder_path)
    
    # Generate naming sequence
    naming_sequence = generate_naming_sequence(len(files_with_time), folder_name)
    renamed_files = []
    
    # Rename files
    for i, (file, _) in enumerate(files_with_time):
        if i < len(naming_sequence):
            old_path = os.path.join(folder_path, file)
            _, ext = os.path.splitext(file)
            new_name = f"{naming_sequence[i]}{ext}"
            new_path = os.path.join(folder_path, new_name)
            os.rename(old_path, new_path)
            renamed_files.append((file, new_name))
    
    return renamed_files

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads, process them, and return a zip file"""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files[]')
    folder_name = request.form.get('folderName', 'renamed_images')
    
    if not files:
        return jsonify({'error': 'No files selected'}), 400
        
    # Create temporary folder for this batch
    batch_folder = os.path.join(app.config['UPLOAD_FOLDER'], 
                               datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(batch_folder)
    
    try:
        # Save uploaded files
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(batch_folder, filename))
        
        # Process the files
        renamed_files = process_images(batch_folder, folder_name)
        
        # Create zip file
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for file in os.listdir(batch_folder):
                file_path = os.path.join(batch_folder, file)
                zf.write(file_path, os.path.join(folder_name, os.path.basename(file_path)))
        
        memory_file.seek(0)
        
        # Cleanup
        shutil.rmtree(batch_folder)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{folder_name}.zip'
        )
        
    except Exception as e:
        if os.path.exists(batch_folder):
            shutil.rmtree(batch_folder)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
