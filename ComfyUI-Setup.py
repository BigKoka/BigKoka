# @title Cài đặt các thư viện cần thiết
!pip install ipywidgets tqdm gitpython piexif -q
import os
import subprocess
import time
import requests
import re
import shutil
import json
from google.colab import drive
from google.colab import output
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from tqdm.notebook import tqdm
from urllib.parse import urlparse
import git

# Thiết lập các biến và cấu trúc dữ liệu
comfyui_folder = '/content/drive/MyDrive/ComfyUI'
version = "latest"

basic_links = {
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

user_links = {category: [] for category in basic_links.keys()}

# Hàm tiện ích
def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    output, error = process.communicate()
    if process.returncode != 0:
        print(f"Lỗi khi chạy lệnh: {command}")
        print(f"Output: {output}")
        print(f"Error: {error}")
        return False
    return True

def create_folders():
    for folder in ['models', 'custom_nodes', 'loras', 'vae', 'controlnet', 'embeddings', 'workflow']:
        os.makedirs(os.path.join(comfyui_folder, folder), exist_ok=True)

def is_git_repo(url):
    return url.endswith('.git') or ('github.com' in url and not url.endswith('.json'))

def clone_or_pull_repo(url, destination):
    if os.path.exists(destination):
        print(f"Thư mục {destination} đã tồn tại. Đang cập nhật...")
        repo = git.Repo(destination)
        repo.remotes.origin.pull()
    else:
        print(f"Đang clone repository {url}...")
        git.Repo.clone_from(url, destination)
    print(f"Đã cập nhật/clone repository {url} thành công!")

def download_file(url, destination):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        print(f"URL không hợp lệ: {url}")
        return False

    os.makedirs(os.path.dirname(destination), exist_ok=True)

    if os.path.exists(destination):
        print(f"File {destination} đã tồn tại. Bỏ qua tải xuống.")
        return True

    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(destination, 'wb') as file:
            file.write(response.content)
        print(f"Đã tải xuống {url} vào {destination}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải xuống {url}: {str(e)}")
        return False

def download_json(url, destination):
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_content = response.json()
        with open(destination, 'w') as f:
            json.dump(json_content, f)
        print(f"Đã tải xuống file JSON từ {url} vào {destination}")
        return json_content
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải xuống từ {url}: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"URL {url} không trả về JSON hợp lệ: {str(e)}")
        print("Nội dung nhận được:")
        print(response.text[:500])
    except Exception as e:
        print(f"Lỗi không xác định khi xử lý {url}: {str(e)}")
    return None

def is_comfyui_ready():
    try:
        response = requests.get('http://localhost:8188')
        return response.status_code == 200
    except:
        return False

def get_cloudflared_url():
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

# Hàm mới để thay thế workflow mặc định
def replace_default_workflow():
    web_folder = os.path.join(comfyui_folder, 'web')
    assets_folder = os.path.join(web_folder, 'assets')
    workflow_basic_path = os.path.join(comfyui_folder, 'workflow', 'workflow_basic.json')

    # Sao chép workflow mới vào thư mục assets
    shutil.copy(workflow_basic_path, os.path.join(assets_folder, 'workflow_basic.json'))

    # Tìm file JavaScript chính
    index_html = os.path.join(web_folder, 'index.html')
    if os.path.exists(index_html):
        with open(index_html, 'r') as f:
            content = f.read()
        match = re.search(r'<script type="module" crossorigin src="([^"]+)"', content)
        if match:
            index_file = os.path.join(web_folder, match.group(1))

            # Thay đổi 'const defaultGraph' thành 'let defaultGraph'
            run_command(f"sed -i 's/const defaultGraph/let defaultGraph/g' {index_file}")

            # Chèn workflow mới vào file JavaScript
            workflow_content = json.dumps(json.load(open(workflow_basic_path)))
            insert_command = f"sed -i '/window\\.comfyAPI\\.defaultGraph\\.defaultGraph/i defaultGraph={workflow_content};' {index_file}"
            run_command(insert_command)

            print("Đã thay thế workflow mặc định thành công!")
        else:
            print("Không tìm thấy script tag trong index.html")
    else:
        print("Không tìm thấy file index.html")

# Hàm xử lý sự kiện
def add_link(b):
    category = category_dropdown.value
    link = link_input.value
    if link:
        if link in basic_links[category] or any(link in user_links[cat] for cat in user_links):
            with status_output:
                print(f"Link '{link}' đã tồn tại trong danh sách.")
        else:
            user_links[category].append(link)
            link_input.value = ''
            update_link_list()
            with status_output:
                print(f"Đã thêm link '{link}' vào danh sách {category}.")

def remove_link(category, link):
    if link in user_links[category]:
        user_links[category].remove(link)
    elif link in basic_links[category]:
        basic_links[category].remove(link)
    update_link_list()

def install_all(b):
    status_output.clear_output()
    with status_output:
        print("Đang mount Google Drive...")
        drive.mount('/content/drive')

        print("Đang cài đặt cloudflared...")
        run_command("wget -q -c https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb")
        run_command("dpkg -i cloudflared-linux-amd64.deb")

        print(f"Đang cài đặt/cập nhật ComfyUI phiên bản {version}...")
        if os.path.exists(comfyui_folder):
            print("Thư mục ComfyUI đã tồn tại. Đang cập nhật...")
            os.chdir(comfyui_folder)
            if run_command("git pull"):
                print("ComfyUI đã được cập nhật thành công!")
            else:
                print("Không thể cập nhật ComfyUI. Đang cài đặt lại...")
                os.chdir('..')
                shutil.rmtree(comfyui_folder)
                os.makedirs(comfyui_folder)
        else:
            os.makedirs(comfyui_folder)

        if not os.path.exists(os.path.join(comfyui_folder, '.git')):
            clone_command = f"git clone {'--branch ' + version if version != 'latest' else ''} https://github.com/comfyanonymous/ComfyUI.git {comfyui_folder}"
            if run_command(clone_command):
                print("ComfyUI đã được clone thành công!")
            else:
                print("Không thể clone repository ComfyUI. Kiểm tra kết nối mạng và thử lại.")
                return

        print("Đang cài đặt các thư viện phụ thuộc...")
        os.chdir(comfyui_folder)
        if run_command("pip install -r requirements.txt"):
            print("Các thư viện phụ thuộc đã được cài đặt thành công!")
        else:
            print("Không thể cài đặt các thư viện phụ thuộc. Kiểm tra lại requirements.txt và thử lại.")
            return

        create_folders()

        for category in basic_links.keys():
            all_links = basic_links[category] + user_links[category]
            for link in all_links:
                if is_git_repo(link):
                    repo_name = os.path.splitext(os.path.basename(link))[0]
                    destination = os.path.join(comfyui_folder, category, repo_name)
                    clone_or_pull_repo(link, destination)
                elif link.endswith('.json'):
                    filename = 'workflow_basic.json' if category == 'workflow' else os.path.basename(link)
                    destination = os.path.join(comfyui_folder, category, filename)
                    download_json(link, destination)
                else:
                    filename = os.path.basename(link)
                    destination = os.path.join(comfyui_folder, category, filename)
                    download_file(link, destination)

        print("Tất cả các mục đã được cài đặt thành công!")

        print("Đang thay thế workflow mặc định...")
        replace_default_workflow()

        print("Đang khởi động ComfyUI...")
        os.chdir(comfyui_folder)
        comfyui_process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("Đang đợi ComfyUI khởi động...")
        timeout = 300  # 5 phút
        start_time = time.time()
        pbar = tqdm(total=timeout, desc="Khởi động ComfyUI", unit="giây")
        while not is_comfyui_ready():
            if time.time() - start_time > timeout:
                print("ComfyUI không khởi động được trong thời gian chờ. Đang in logs...")
                output, error = comfyui_process.communicate()
                print("Output:", output.decode())
                print("Error:", error.decode())
                pbar.close()
                return
            time.sleep(1)
            pbar.update(1)
        pbar.close()

        print("\nComfyUI đã sẵn sàng!")

        print("Đang khởi động Cloudflared và lấy URL...")
        url = get_cloudflared_url()
        if url:
            print(f"ComfyUI có thể truy cập tại URL: {url}")
        else:
            print("Không thể lấy được URL từ Cloudflared. Đang thử các phương án khác...")

        print("Kiểm tra port forwarding của Google Colab...")
        output.serve_kernel_port_as_window(8188)
        print("Vui lòng kiểm tra URL được tạo bởi Colab ở trên.")

        print("Nếu bạn vẫn không thấy URL, hãy kiểm tra tab 'Tools' > 'Ports' trong Google Colab để tìm URL truy cập cho cổng 8188.")

def update_link_list():
    table_html = '''
    <table style="width:100%; border-collapse: collapse;">
    <tr>
    <th style="border: 1px solid black; padding: 5px;">Nơi lưu file</th>
    <th style="border: 1px solid black; padding: 5px;">Link cần tải</th>
    <th style="border: 1px solid black; padding: 5px;">Xóa link</th>
    </tr>
    '''
    for category in basic_links.keys():
        for link in basic_links[category] + user_links[category]:
            table_html += f'''
            <tr>
            <td style="border: 1px solid black; padding: 5px;">{category}</td>
            <td style="border: 1px solid black; padding: 5px;">{link}</td>
            <td style="border: 1px solid black; padding: 5px;">
            <button onclick="remove_link('{category}', '{link}')">Remove</button>
            </td>
            </tr>
            '''
    table_html += '</table>'
    link_list.value = table_html

# Tạo widgets
category_dropdown = widgets.Dropdown(options=list(basic_links.keys()), description='Category:')
link_input = widgets.Text(description='Link:')
add_button = widgets.Button(description='Add Link')
install_all_button = widgets.Button(description='Install All')
link_list = widgets.HTML()
status_output = widgets.Output()

# Thiết lập xử lý sự kiện
add_button.on_click(add_link)
install_all_button.on_click(install_all)

# Tạo layout
app = widgets.VBox([
    widgets.HBox([category_dropdown, link_input, add_button]),
    link_list,
    install_all_button,
    status_output
])

# JavaScript để xử lý nút Remove
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

# Cập nhật danh sách link ban đầu
update_link_list()
