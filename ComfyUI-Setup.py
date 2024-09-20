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

# Khởi tạo danh sách liên kết mới
new_links = {category: [] for category in BASIC_LINKS.keys()}

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
    elif link in new_links[category]:
        new_links[category].remove(link)
    update_link_list()
    update_new_link_list()

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

def update_new_link_list():
    """Cập nhật danh sách liên kết mới hiển thị"""
    table_html = '''
    <table style="width:100%; border-collapse: collapse;">
    <tr>
    <th style="border: 1px solid black; padding: 5px;">Danh mục</th>
    <th style="border: 1px solid black; padding: 5px;">Liên kết</th>
    <th style="border: 1px solid black; padding: 5px;">Xóa</th>
    </tr>
    '''
    for category in new_links.keys():
        for link in new_links[category]:
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
    new_link_list.value = table_html

def add_new_link(b):
    """Thêm liên kết mới vào danh sách mới"""
    category = new_category_dropdown.value
    link = new_link_input.value.strip()
    if link:
        if link in new_links[category]:
            with new_status_output:
                print(f"Liên kết '{link}' đã tồn tại trong danh sách mới.")
        else:
            new_links[category].append(link)
            new_link_input.value = ''
            update_new_link_list()
            with new_status_output:
                print(f"Đã thêm liên kết '{link}' vào danh sách mới {category}.")

def install_new_links(b):
    """Tải và cài đặt các liên kết mới"""
    with new_status_output:
        print("Đang tải và cài đặt các liên kết mới...")
        for category, links in new_links.items():
            for link in links:
                if is_git_repo(link):
                    repo_name = os.path.splitext(os.path.basename(link))[0]
                    destination = os.path.join(COMFYUI_FOLDER, category, repo_name)
                    clone_or_pull_repo(link, destination)
                elif link.endswith('.json'):
                    filename = os.path.basename(link)
                    destination = os.path.join(WORKFLOW_FOLDER, filename)
                    download_json(link, destination)
                else:
                    filename = os.path.basename(link)
                    destination = os.path.join(COMFYUI_FOLDER, category, filename)
                    download_file(link, destination)
        print("Tất cả các liên kết mới đã được tải và cài đặt thành công!")
        # Xóa danh sách liên kết mới sau khi cài đặt
        for category in new_links:
            new_links[category] = []
        update_new_link_list()

# Tạo các widget
category_dropdown = widgets.Dropdown(options=list(BASIC_LINKS.keys()), description='Danh mục:')
link_input = widgets.Text(description='Liên kết:')
add_button = widgets.Button(description='Thêm Liên kết')
install_all_button = widgets.Button(description='Cài đặt Tất cả')
link_list = widgets.HTML()
status_output = widgets.Output()

# Tạo các widget mới cho chức năng tải thêm
new_category_dropdown = widgets.Dropdown(options=list(BASIC_LINKS.keys()), description='Danh mục mới:')
new_link_input = widgets.Text(description='Liên kết mới:')
add_new_button = widgets.Button(description='Tải thêm')
install_new_button = widgets.Button(description='Tải thêm & Cài đặt')
new_link_list = widgets.HTML()
new_status_output = widgets.Output()

# Thiết lập xử lý sự kiện
add_button.on_click(add_link)
install_all_button.on_click(install_all)
add_new_button.on_click(add_new_link)
install_new_button.on_click(install_new_links)

# Tạo layout
app = widgets.VBox([
    widgets.HBox([category_dropdown, link_input, add_button]),
    link_list,
    install_all_button,
    status_output,
    widgets.HTML("<hr>"),  # Đường phân cách
    widgets.HTML("<h3>Tải thêm thành phần mới</h3>"),
    widgets.HBox([new_category_dropdown, new_link_input, add_new_button]),
    new_link_list,
    install_new_button,
    new_status_output
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
update_new_link_list()
