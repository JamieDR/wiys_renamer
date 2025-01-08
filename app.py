from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime
import zipfile
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def generate_naming_sequence(count):
    if count < 2:
        return ["1 Intro"]
    sequence = ["1 Intro"] + [f"{i} {chr(96 + i)}" for i in range(2, count)]
    sequence.append("FEATURED")
    return sequence

def process_images(folder_path):
    files = [f for f in os.listdir(folder_path) 
             if f.lower().endswith('.jpg') and os.path.isfile(os.path.join(folder_path, f))]
    
    files_with_time = [(file, os.path.getctime(os.path.join(folder_path, file))) 
                       for file in files]
    files_with_time.sort(key=lambda x: x[1])
    
    naming_sequence = generate_naming_sequence(len(files_with_time))
    renamed_files = []
    
    for i, (file, _) in enumerate(files_with_time):
        old_path = os.path.join(folder_path, file)
        new_name = f"{naming_sequence[i]}.jpg"
        new_path = os.path.join(folder_path, new_name)
        os.rename(old_path, new_path)
        renamed_files.append((file, new_name))
    
    return renamed_files

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files[]')
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
        renamed_files = process_images(batch_folder)
        
        # Create zip file
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for file in os.listdir(batch_folder):
                file_path = os.path.join(batch_folder, file)
                zf.write(file_path, os.path.basename(file_path))
        
        memory_file.seek(0)
        
        # Cleanup
        shutil.rmtree(batch_folder)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='renamed_images.zip'
        )
        
    except Exception as e:
        if os.path.exists(batch_folder):
            shutil.rmtree(batch_folder)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
