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
from google.colab import drive, output
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from tqdm import tqdm
from urllib.parse import urlparse
import git
from google.colab import output as colab_output

# Cấu hình
COMFYUI_FOLDER = '/content/drive/MyDrive/ComfyUI'
VERSION = "latest"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"

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
        'https://raw.githubusercontent.com/BigKoka/BigKoka/main/workflow-comfyui---flux-portrait-master-v3.json'
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
            disable=True, # Thêm dòng này
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
                elif link.endswith('.json'):
                    filename = os.path.basename(link)
                    destination = os.path.join(COMFYUI_FOLDER, category, filename)
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
        with tqdm(total=timeout, desc="Đang khởi động ComfyUI", unit="giây") as pbar:
            while not is_comfyui_ready():
                if time.time() - start_time > timeout:
                    print("ComfyUI không thể khởi động trong thời gian chờ. Đang in log...")
                    output, error = comfyui_process.communicate()
                    print("Đầu ra:", output.decode())
                    print("Lỗi:", error.decode())
                    return
                time.sleep(1)
                pbar.update(1)

        print("\nComfyUI đã sẵn sàng!")

        print("Đang khởi động Cloudflared và lấy URL...")
        url = get_cloudflared_url()
        if url:
            print(f"ComfyUI có thể truy cập tại: {url}")
        else:
            print("Không thể lấy URL từ Cloudflared. Đang thử phương pháp thay thế...")

        print("Đang kiểm tra chuyển tiếp cổng Google Colab...")
        colab_output.serve_kernel_port_as_window(8188)
        print("Vui lòng kiểm tra URL được tạo bởi Colab ở trên.")

        print("Nếu bạn vẫn không thấy URL, hãy kiểm tra tab 'Tools' > 'Ports' trong Google Colab để tìm URL truy cập cho cổng 8188.")

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

    for node in workflow.get('nodes', []):
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


def check_workflow(b):
    """Kiểm tra workflow khi người dùng nhấn nút"""
    url = workflow_input.value.strip()
    if not url:
        with workflow_output:
            print("Vui lòng nhập URL của workflow.")
        return

    workflow = download_workflow(url)
    if workflow:
        try:
            required_components = analyze_workflow(workflow)
            with workflow_output:
                clear_output()
                print("Các thành phần cần thiết cho workflow:")
                for category, items in required_components.items():
                    if items:
                        print(f"\n{category.capitalize()}:")
                        for item in items:
                            print(f"- {item}")

                if all(len(items) == 0 for items in required_components.values()):
                    print("\nKhông tìm thấy thành phần cụ thể nào. Workflow có thể không cần thêm thành phần hoặc sử dụng cấu trúc khác.")
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
