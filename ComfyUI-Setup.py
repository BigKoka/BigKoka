# @title Cài đặt và Chạy ComfyUI trên Google Colab

# Cài đặt các thư viện cần thiết
!pip install ipywidgets tqdm gitpython requests -q

# Import các thư viện cần thiết
import os
import subprocess
import time
import requests
import re
import shutil
import json
from google.colab import drive, output, files
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from tqdm.notebook import tqdm
from urllib.parse import urlparse
import git
from google.colab import output as colab_output
import io

# Cấu hình
COMFYUI_FOLDER = '/content/drive/MyDrive/ComfyUI'
VERSION = "latest"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
WORKFLOW_FOLDER = "/content/drive/MyDrive/ComfyUI/user/default/workflows"

# Định nghĩa các liên kết cơ bản
BASIC_LINKS = {
    'models': [],
    'extensions': [],
    'custom_nodes': [
        'https://github.com/florestefano1975/comfyui-portrait-master',
        'https://github.com/giriss/comfy-image-saver',
        'https://github.com/XLabs-AI/x-flux-comfyui',
        'https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes',
        'https://github.com/ltdrdata/ComfyUI-Manager',
    ],
    'loras': [],
    'vae': [],
    'controlnet': [],
    'embeddings': [],
    'workflow': [
        'https://raw.githubusercontent.com/BigKoka/BigKoka/main/workflow-comfyui---flux-portrait-master-v3.json',
        'https://github.com/BigKoka/workflow-duc'
    ]
}

# Khởi tạo danh sách liên kết của người dùng
user_links = {category: [] for category in BASIC_LINKS.keys()}

def run_command(command):
    """Chạy lệnh shell và trả về kết quả"""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    cmd_output, error = process.communicate()
    if process.returncode != 0:
        print(f"Lỗi khi chạy lệnh: {command}")
        print(f"Đầu ra: {cmd_output}")
        print(f"Lỗi: {error}")
        return False
    return True

def create_folders():
    """Tạo các thư mục cần thiết"""
    for folder in BASIC_LINKS.keys():
        os.makedirs(os.path.join(COMFYUI_FOLDER, folder), exist_ok=True)
    os.makedirs(WORKFLOW_FOLDER, exist_ok=True)

def is_git_repo(url):
    """Kiểm tra xem URL có phải là một repository Git không"""
    return url.endswith('.git') or ('github.com' in url and not url.endswith('.json'))

def clone_or_pull_repo(url, destination):
    """Clone hoặc cập nhật repository Git"""
    try:
        if os.path.exists(destination):
            print(f"Đang cập nhật repository hiện có: {destination}")
            repo = git.Repo(destination)
            repo.remotes.origin.pull()
        else:
            print(f"Đang clone repository: {url}")
            git.Repo.clone_from(url, destination)
        print(f"Đã cập nhật/clone repository thành công: {url}")
        return True
    except git.GitCommandError as e:
        print(f"Thao tác Git thất bại cho {url}: {str(e)}")
        return False

def download_file(url, destination):
    """Tải xuống file từ URL"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(destination), exist_ok=True)

        if os.path.exists(destination):
            print(f"File đã tồn tại: {destination}. Bỏ qua tải xuống.")
            return True

        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192

        with open(destination, 'wb') as file, tqdm(
            desc=os.path.basename(destination),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            disable=True,
        ) as progress_bar:
            for data in response.iter_content(block_size):
                size = file.write(data)
                progress_bar.update(size)

        print(f"Đã tải xuống {url} vào {destination}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải xuống {url}: {str(e)}")
        return False

def download_json(url, destination):
    """Tải xuống và lưu file JSON"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_content = response.json()
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w') as f:
            json.dump(json_content, f, indent=2)
        print(f"Đã tải xuống JSON từ {url} vào {destination}")
        return json_content
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải xuống từ {url}: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON không hợp lệ từ {url}: {str(e)}")
        print("Nội dung nhận được:")
        print(response.text[:500])
    except Exception as e:
        print(f"Lỗi không mong đợi khi xử lý {url}: {str(e)}")
    return None

def is_comfyui_ready():
    """Kiểm tra xem ComfyUI đã sẵn sàng chưa"""
    try:
        response = requests.get('http://localhost:8188', timeout=5)
        return response.status_code == 200
    except:
        return False

def get_cloudflared_url():
    """Lấy URL từ Cloudflared"""
    process = subprocess.Popen(['cloudflared', 'tunnel', '--url', 'http://localhost:8188'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)

    for line in process.stdout:
        print(line.strip())
        match = re.search(r'(https://.*\.trycloudflare\.com)', line)
        if match:
            return match.group(1)

    return None

def add_link(b):
    """Thêm liên kết mới vào danh sách"""
    category = category_dropdown.value
    link = link_input.value.strip()
    if link:
        if link in BASIC_LINKS[category] or any(link in user_links[cat] for cat in user_links):
            with status_output:
                print(f"Liên kết '{link}' đã tồn tại trong danh sách.")
        else:
            user_links[category].append(link)
            link_input.value = ''
            update_link_list()
            with status_output:
                print(f"Đã thêm liên kết '{link}' vào danh sách {category}.")

def remove_link(category, link):
    """Xóa liên kết khỏi danh sách"""
    if link in user_links[category]:
        user_links[category].remove(link)
    elif link in BASIC_LINKS[category]:
        BASIC_LINKS[category].remove(link)
    update_link_list()

def install_all(b):
    """Cài đặt tất cả các thành phần"""
    status_output.clear_output()
    with status_output:
        print("Đang kết nối Google Drive...")
        drive.mount('/content/drive')

        print("Đang cài đặt cloudflared...")
        if not run_command(f"wget -q -c {CLOUDFLARED_URL} && dpkg -i cloudflared-linux-amd64.deb"):
            print("Không thể cài đặt cloudflared. Tiếp tục mà không có nó.")

        print(f"Đang cài đặt/cập nhật ComfyUI phiên bản {VERSION}...")
        if os.path.exists(COMFYUI_FOLDER):
            print("Thư mục ComfyUI đã tồn tại. Đang cập nhật...")
            os.chdir(COMFYUI_FOLDER)
            if not run_command("git pull"):
                print("Không thể cập nhật ComfyUI. Đang cài đặt lại...")
                os.chdir('..')
                shutil.rmtree(COMFYUI_FOLDER)
                os.makedirs(COMFYUI_FOLDER)
        else:
            os.makedirs(COMFYUI_FOLDER)

        if not os.path.exists(os.path.join(COMFYUI_FOLDER, '.git')):
            clone_command = f"git clone {'--branch ' + VERSION if VERSION != 'latest' else ''} https://github.com/comfyanonymous/ComfyUI.git {COMFYUI_FOLDER}"
            if not run_command(clone_command):
                print("Không thể clone repository ComfyUI. Kiểm tra kết nối internet và thử lại.")
                return

        print("Đang cài đặt các phụ thuộc...")
        os.chdir(COMFYUI_FOLDER)
        if not run_command("pip install -r requirements.txt"):
            print("Không thể cài đặt các phụ thuộc. Kiểm tra file requirements.txt và thử lại.")
            return

        create_folders()

        for category in BASIC_LINKS.keys():
            all_links = BASIC_LINKS[category] + user_links[category]
            for link in all_links:
                if is_git_repo(link):
                    repo_name = os.path.splitext(os.path.basename(link))[0]
                    destination = os.path.join(COMFYUI_FOLDER, category, repo_name)
                    clone_or_pull_repo(link, destination)
                    if category == 'workflow':
                        # Copy all JSON files from the cloned repo to the workflow folder
                        for root, dirs, files in os.walk(destination):
                            for file in files:
                                if file.endswith('.json'):
                                    shutil.copy(os.path.join(root, file), WORKFLOW_FOLDER)
                elif link.endswith('.json'):
                    filename = os.path.basename(link)
                    destination = os.path.join(WORKFLOW_FOLDER, filename)
                    download_json(link, destination)
                else:
                    filename = os.path.basename(link)
                    destination = os.path.join(COMFYUI_FOLDER, category, filename)
                    download_file(link, destination)

        print("Tất cả các mục đã được cài đặt thành công!")

        print("Đang khởi động ComfyUI...")
        os.chdir(COMFYUI_FOLDER)
        comfyui_process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("Đang đợi ComfyUI khởi động...")
        timeout = 300  # 5 phút
        start_time = time.time()
        with tqdm(total=timeout, desc="Đang khởi động ComfyUI", unit="giây", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as progress_bar:
            while not is_comfyui_ready():
                if time.time() - start_time > timeout:
                    print("\nComfyUI không thể khởi động trong thời gian chờ. Đang in log...")
                    output, error = comfyui_process.communicate()
                    print("Đầu ra:", output.decode())
                    print("Lỗi:", error.decode())
                    return
                time.sleep(1)
                progress_bar.update(1)

        print("\nComfyUI đã sẵn sàng!")

        print("Đang khởi động Cloudflared và lấy URL...")
        url = get_cloudflared_url()
        if url:
            print(f"ComfyUI có thể truy cập tại: {url}")
        else:
            print("Không thể lấy URL từ Cloudflared. Đang thử phương pháp thay thế...")

        print("Vui lòng kiểm tra tab 'Tools' > 'Ports' trong Google Colab để tìm URL truy cập cho cổng 8188.")

def update_link_list():
    """Cập nhật danh sách liên kết hiển thị"""
    table_html = '''
    <table style="width:100%; border-collapse: collapse;">
    <tr>
    <th style="border: 1px solid black; padding: 5px;">Danh mục</th>
    <th style="border: 1px solid black; padding: 5px;">Liên kết</th>
    <th style="border: 1px solid black; padding: 5px;">Xóa</th>
    </tr>
    '''
    for category in BASIC_LINKS.keys():
        for link in BASIC_LINKS[category] + user_links[category]:
            table_html += f'''
            <tr>
            <td style="border: 1px solid black; padding: 5px;">{category}</td>
            <td style="border: 1px solid black; padding: 5px;">{link}</td>
            <td style="border: 1px solid black; padding: 5px;">
            <button onclick="remove_link('{category}', '{link}')">Xóa</button>
            </td>
            </tr>
            '''
    table_html += '</table>'
    link_list.value = table_html

def download_workflow(url):
    """Tải về file JSON workflow từ URL được cung cấp"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải workflow: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Lỗi khi giải mã JSON: {str(e)}")
        return None

def analyze_workflow(workflow):
    required_components = {
        'custom_nodes': set(),
        'models': set(),
        'checkpoints': set(),
        'vae': set(),
        'clip': set(),
        'loras': set(),
        'controlnet': set(),
        'embeddings': set(),
        'extensions': set()
    }

    nodes = workflow.get('nodes', [])

    for node in nodes:
        node_type = node.get('type', '')

        # Phát hiện custom nodes
        if node_type not in ['KSamplerSelect', 'VAEDecode', 'CLIPTextEncode', 'EmptyLatentImage', 'RandomNoise']:
            required_components['custom_nodes'].add(node_type)

        # Xử lý các node loader
        if node_type == 'UNETLoader':
            required_components['models'].add(node['widgets_values'][0])
        elif node_type == 'VAELoader':
            required_components['vae'].add(node['widgets_values'][0])
        elif node_type == 'DualCLIPLoader':
            required_components['clip'].update(node['widgets_values'][:2])

        # Xử lý các input và widget values
        for input_data in node.get('inputs', []):
            if isinstance(input_data, dict) and 'widget' in input_data:
                widget_name = input_data['widget'].get('name')
                if widget_name in ['ckpt_name', 'vae_name', 'clip_name', 'lora_name']:
                    category = widget_name.split('_')[0]
                    value = node['widgets_values'][input_data['slot_index']]
                    required_components[category + 's'].add(value)

    return required_components

def analyze_workflow_details(workflow):
    """Tạo tóm tắt chi tiết về cách thức hoạt động của workflow dựa trên file JSON"""
    nodes = workflow.get('nodes', [])
    sorted_nodes = sorted(nodes, key=lambda x: x.get('id', 0))

    # Phân loại nodes
    categories = {
        "Khởi tạo": [],
        "Xử lý Prompt": [],
        "Mã hóa CLIP & Điều hướng": [],
        "Sampling (Tạo ảnh)": [],
        "Xử lý kết quả": [],
        "Khác": []
    }

    for node in sorted_nodes:
        node_type = node.get('type', '')
        if node_type in ['UNETLoader', 'VAELoader', 'CLIPLoader', 'LoraLoader', 'EmptyLatentImage', 'RandomNoise']:
            categories["Khởi tạo"].append(node)
        elif 'Text' in node_type or 'Prompt' in node_type:
            categories["Xử lý Prompt"].append(node)
        elif 'CLIP' in node_type or 'Encode' in node_type:
            categories["Mã hóa CLIP & Điều hướng"].append(node)
        elif 'Sampler' in node_type or 'KSampler' in node_type:
            categories["Sampling (Tạo ảnh)"].append(node)
        elif node_type in ['VAEDecode', 'SaveImage', 'PreviewImage']:
            categories["Xử lý kết quả"].append(node)
        else:
            categories["Khác"].append(node)

    # Tạo tóm tắt
    summary = ["Workflow này được thiết kế để tạo ra hình ảnh bằng ComfyUI, sử dụng các mô hình và kỹ thuật xử lý prompt nâng cao."]

    for category, category_nodes in categories.items():
        if category_nodes:
            summary.append(f"**{category}:**")
            for node in category_nodes:
                node_type = node.get('type', '')
                node_inputs = node.get('inputs', [])
                node_widgets = node.get('widgets_values', [])
                
                description = f"* **{node_type}:** "
                
                if node_type == 'UNETLoader':
                    description += f"Tải mô hình UNET {node_widgets[0] if node_widgets else 'không xác định'}."
                elif node_type == 'VAELoader':
                    description += f"Tải mô hình VAE {node_widgets[0] if node_widgets else 'không xác định'}."
                elif node_type == 'CLIPLoader' or node_type == 'CLIPTextEncode':
                    description += f"Tải/sử dụng CLIP model {node_widgets[0] if node_widgets else 'không xác định'}."
                elif node_type == 'EmptyLatentImage':
                    width, height = node_widgets[:2] if len(node_widgets) >= 2 else ('không xác định', 'không xác định')
                    description += f"Tạo ảnh latent trống kích thước {width}x{height}."
                elif node_type == 'RandomNoise':
                    description += f"Tạo noise ngẫu nhiên với seed {node_widgets[0] if node_widgets else 'không xác định'}."
                elif 'KSampler' in node_type:
                    sampler = node_widgets[0] if node_widgets else 'không xác định'
                    steps = node_widgets[1] if len(node_widgets) > 1 else 'không xác định'
                    description += f"Sử dụng sampler {sampler} với {steps} steps."
                elif node_type == 'SaveImage':
                    description += "Lưu ảnh đã tạo."
                elif node_type == 'PreviewImage':
                    description += "Hiển thị ảnh để preview."
                else:
                    description += "Xử lý dữ liệu."
                
                summary.append(description)

    summary.append("**Tóm lại:** Workflow này sử dụng các mô hình đã được tải để tạo ảnh, bao gồm các bước: khởi tạo mô hình và dữ liệu, xử lý prompt, mã hóa CLIP, sampling để tạo ảnh, và cuối cùng là xử lý kết quả (hiển thị và lưu ảnh).")

    return "\n".join(summary)

def get_workflow_process(workflow):
    """Phân tích quy trình hoạt động của workflow"""
    process = []
    nodes = workflow.get('nodes', [])

    # Sắp xếp nodes theo thứ tự thực hiện
    sorted_nodes = sorted(nodes, key=lambda x: x.get('id', 0))

    for node in sorted_nodes:
        node_type = node.get('type', '')
        inputs = node.get('inputs', [])
        outputs = node.get('outputs', [])

        step = f"Node: {node_type}\n"

        if inputs:
            step += "Inputs:\n"
            for input_data in inputs:
                input_name = input_data.get('name', 'Unknown')
                input_type = input_data.get('type', 'Unknown')
                step += f"  - {input_name}: {input_type}\n"

        if outputs:
            step += "Outputs:\n"
            for output in outputs:
                step += f"  - {output.get('name', 'Unknown')}: {output.get('type', 'Unknown')}\n"

        process.append(step)

    return "\n".join(process)

def check_workflow(b):
    """Kiểm tra workflow khi người dùng nhấn nút"""
    url = workflow_input.value.strip()
    if not url:
        with workflow_output:
            print("Vui lòng nhập URL của workflow.")
        return

    with workflow_output:
        clear_output()
        print(f"Đang tải workflow từ URL: {url}")
        
    workflow = download_workflow(url)
    
    if workflow:
        try:
            with workflow_output:
                print("Đã tải workflow thành công. Đang phân tích...")

            required_components = analyze_workflow(workflow)
            workflow_details = analyze_workflow_details(workflow)

            with workflow_output:
                print("Lưu ý: Tất cả thông tin dưới đây được trích xuất trực tiếp từ file JSON workflow tải về từ URL bạn cung cấp.")
                print("---")

            with workflow_output:
                print("\nKết quả phân tích workflow:")
                print("\nCác thành phần cần thiết cho workflow:")
                for category, items in required_components.items():
                    if items:
                        print(f"\n{category.capitalize()}:")
                        for item in items:
                            print(f"- {item}")

                if all(len(items) == 0 for items in required_components.values()):
                    print("\nKhông tìm thấy thành phần cụ thể nào. Workflow có thể không cần thêm thành phần hoặc sử dụng cấu trúc khác.")

                print("\nTóm tắt cách thức hoạt động của workflow:")
                print(workflow_details)

                # Lưu workflow vào bộ nhớ đệm
                filename = os.path.basename(urlparse(url).path)
                if not filename.endswith('.json'):
                    filename += '.json'
                save_path = os.path.join(WORKFLOW_FOLDER, filename)
                with open(save_path, 'w') as f:
                    json.dump(workflow, f, indent=2)
                print(f"\nĐã lưu workflow vào: {save_path}")

                # Thêm link vào BASIC_LINKS
                if url not in BASIC_LINKS['workflow']:
                    BASIC_LINKS['workflow'].append(url)
                    print(f"\nĐã thêm link workflow vào danh sách cần tải: {url}")
                    update_link_list()
                else:
                    print(f"\nLink workflow đã tồn tại trong danh sách cần tải.")

        except Exception as e:
            with workflow_output:
                print(f"Lỗi khi phân tích workflow: {str(e)}")
                print("Cấu trúc workflow có thể không đúng như mong đợi.")
    else:
        with workflow_output:
            print("Không thể tải workflow. Vui lòng kiểm tra URL và thử lại.")
# Tạo các widget
category_dropdown = widgets.Dropdown(options=list(BASIC_LINKS.keys()), description='Danh mục:')
link_input = widgets.Text(description='Liên kết:')
add_button = widgets.Button(description='Thêm Liên kết')
install_all_button = widgets.Button(description='Cài đặt Tất cả')
link_list = widgets.HTML()
status_output = widgets.Output()

# Tạo các widget mới cho chức năng kiểm tra workflow
workflow_input = widgets.Text(description='URL Workflow:', style={'description_width': 'initial'})
check_workflow_button = widgets.Button(description='Kiểm tra Workflow')
workflow_output = widgets.Output()

# Thiết lập xử lý sự kiện
add_button.on_click(add_link)
install_all_button.on_click(install_all)
check_workflow_button.on_click(check_workflow)

# Tạo layout
app = widgets.VBox([
    widgets.HBox([workflow_input, check_workflow_button]),
    workflow_output,
    widgets.HBox([category_dropdown, link_input, add_button]),
    link_list,
    install_all_button,
    status_output
])

# JavaScript để xử lý nút Xóa
js = """
<script>
function remove_link(category, link) {
    google.colab.kernel.invokeFunction('notebook.remove_link', [category, link], {});
}
</script>
"""
display(HTML(js))

# Đăng ký hàm Python để được gọi từ JavaScript
output.register_callback('notebook.remove_link', remove_link)

# Hiển thị ứng dụng
display(app)

# Cập nhật danh sách liên kết ban đầu
update_link_list()
