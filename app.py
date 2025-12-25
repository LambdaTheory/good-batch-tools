from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import time
import pandas as pd
from alipay_api import AlipayAPI
from excel_handler import ExcelHandler

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
IMAGE_MAP_FILE = 'image_map.json'

# Load image map
if os.path.exists(IMAGE_MAP_FILE):
    try:
        with open(IMAGE_MAP_FILE, 'r', encoding='utf-8') as f:
            image_map = json.load(f)
    except:
        image_map = {}
else:
    image_map = {}

def save_image_map():
    with open(IMAGE_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(image_map, f, ensure_ascii=False, indent=2)

# Initialize API wrapper (will be configured by user input)
alipay = AlipayAPI()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/alipay-goods')
def alipay_goods():
    return render_template('alipay_goods.html')

@app.route('/mini-program-goods')
def mini_program_goods():
    return render_template('mini_program_goods.html')

@app.route('/config', methods=['POST'])
def update_config():
    data = request.json
    alipay.update_config(data.get('cookie'), data.get('ctoken'))
    return jsonify({"status": "success", "message": "Configuration updated", "ctoken": alipay.ctoken})

@app.route('/get-template', methods=['GET'])
def get_template():
    try:
        with open('template.json', 'r', encoding='utf-8') as f:
            template = json.load(f)
        return jsonify({"status": "success", "template": template})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})
    
    # Get folder from form data, default to 'default'
    folder = request.form.get('folder', 'default')
    # Sanitize folder name (simple)
    folder = "".join([c for c in folder if c.isalnum() or c in (' ', '_', '-')]).strip()
    if not folder: folder = 'default'

    # Save locally
    filename = file.filename
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(folder_path, exist_ok=True)
    
    filepath = os.path.join(folder_path, filename)
    file.save(filepath)
    
    # Re-open for upload
    import werkzeug.datastructures
    with open(filepath, 'rb') as f:
        file_obj = werkzeug.datastructures.FileStorage(f, filename=filename, name='file')
        result = alipay.upload_image(file_obj)

    if result.get('status') == 'success':
        # Update map
        # Key is now folder/filename to support same filename in different folders
        map_key = f"{folder}/{filename}"
        image_map[map_key] = {
            "name": filename,
            "folder": folder,
            "url": result['url'],
            "fileId": result['fileId'],
            "imageId": result['imageId'],
            "status": "success",
            "uploadTime": time.time()
        }
        save_image_map()
        
    return jsonify(result)

@app.route('/delete-image', methods=['POST'])
def delete_image():
    data = request.json
    folder = data.get('folder', 'default')
    name = data.get('name')
    
    if not name:
        return jsonify({"status": "error", "message": "Missing name"})
        
    map_key = f"{folder}/{name}"
    
    # Remove from map
    if map_key in image_map:
        del image_map[map_key]
        save_image_map()
        
    # Delete local file
    try:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        filepath = os.path.join(folder_path, name)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Try to remove folder if empty
            try:
                os.rmdir(folder_path)
            except:
                pass
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get-images', methods=['GET'])
def get_images():
    # Return list of images sorted by time
    # Ensure backward compatibility for items without 'folder'
    images = []
    for k, v in image_map.items():
        if 'folder' not in v:
            v['folder'] = 'default' # Assign default if missing
        images.append(v)
        
    images.sort(key=lambda x: x.get('uploadTime', 0), reverse=True)
    return jsonify({"status": "success", "images": images})

@app.route('/download-excel-template')
def download_excel_template():
    # Create a DataFrame with example data showing a multi-SKU product
    # Logic: Rows with the same "商家商品编码" will be grouped into one product
    data = {
        "类目ID(必填)": ["C001627013", "C001627013"], 
        "商品标题(必填)": ["富士拍立得(多规格示例)", "富士拍立得(多规格示例)"],
        "商家商品编码(必填,用于分组)": ["ITEM_MULTI_001", "ITEM_MULTI_001"],
        "商品详情页地址(必填)": ["https://detail.tmall.com/item.htm?id=1", "https://detail.tmall.com/item.htm?id=1"],
        "增值服务价格(元)": [20, 20],
        "起租天数(默认1)": [1, 1],
        "成色等级(默认99新)": ["99新", "99新"],
        "商家SKU编码": ["SKU_A_001", "SKU_B_002"],
        "最低日单价(元)": [10, 15],
        "SKU规格名称": ["套餐一(单机)", "套餐二(含相纸)"],
        "SKU租期(天,逗号分隔)": ["1,3,7", "1,3,7"],
        "SKU租期总价(元,格式 天数:价格,逗号分隔)": ["1:50,3:120,7:200", "1:60,3:150,7:250"],
        "每日库存数量": [20, 10]
    }
    df = pd.DataFrame(data)
    
    template_path = 'goods_template.xlsx'
    df.to_excel(template_path, index=False)
    
    return send_file(template_path, as_attachment=True, download_name='goods_template.xlsx')

@app.route('/parse-excel', methods=['POST'])
def parse_excel():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    
    handler = ExcelHandler(filepath)
    data = handler.parse()
    return jsonify({"status": "success", "data": data})

@app.route('/create-goods', methods=['POST'])
def create_goods():
    data = request.json
    results = []
    for item in data.get('items', []):
        res = alipay.create_good(item)
        results.append(res)
    return jsonify({"status": "success", "results": results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
