# @title
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

# Cài đặt ipywidgets và tqdm nếu chưa có
!pip install ipywidgets tqdm -q

# Thiết lập các biến và cấu trúc dữ liệu
comfyui_folder = '/content/drive/MyDrive/ComfyUI'
version = "latest"
default_workflow_url = "https://raw.githubusercontent.com/comfyanonymous/ComfyUI_examples/main/examples/example_workflow.json"

basic_links = {
    'models': [],
    'extensions': [],
    'custom_nodes': [
        'https://github.com/florestefano1975/comfyui-portrait-master',
        'https://github.com/giriss/comfy-image-saver',
        'https://github.com/XLabs-AI/x-flux-comfyui',
        'https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes'
    ],
    'loras': [],
    'vae': [],
    'controlnet': [],
    'embeddings': [],
    'workflow': []
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
    for folder in ['models', 'extensions', 'custom_nodes', 'loras', 'vae', 'controlnet', 'embeddings', 'workflow']:
        os.makedirs(os.path.join(comfyui_folder, folder), exist_ok=True)

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

def setup_default_workflow():
    workflow_folder = os.path.join(comfyui_folder, 'workflow')
    comfyui_workflow_folder = os.path.join(comfyui_folder, 'web', 'workflows')
    os.makedirs(comfyui_workflow_folder, exist_ok=True)

    workflow_files = [f for f in os.listdir(workflow_folder) if f.endswith('.json')]

    if not workflow_files:
        print("Không tìm thấy file workflow nào trong thư mục workflow. Đang tải workflow mặc định...")
        default_workflow_filename = os.path.basename(urlparse(default_workflow_url).path)
        default_workflow_path = os.path.join(workflow_folder, default_workflow_filename)
        if download_file(default_workflow_url, default_workflow_path):
            workflow_files = [default_workflow_filename]
        else:
            print("Không thể tải workflow mặc định. Vui lòng kiểm tra kết nối mạng và thử lại.")
            return

    for filename in workflow_files:
        src = os.path.join(workflow_folder, filename)
        dst = os.path.join(comfyui_workflow_folder, filename)
        shutil.copy(src, dst)
        print(f"Đã tải workflow: {filename}")

    latest_workflow = max(
        [f for f in os.listdir(comfyui_workflow_folder) if f.endswith('.json')],
        key=lambda f: os.path.getmtime(os.path.join(comfyui_workflow_folder, f))
    )

    config_path = os.path.join(comfyui_folder, 'web', 'scripts', 'config.js')

    if not os.path.exists(config_path):
        print(f"Không tìm thấy file config.js tại {config_path}. Đang tạo file mới...")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write('app_config = {};\n')

    with open(config_path, 'r') as f:
        config = f.read()

    config = re.sub(r'app_config\.default_workflow\s*=\s*".*?";', f'app_config.default_workflow = "{latest_workflow}";', config)

    if 'app_config.default_workflow' not in config:
        config += f'\napp_config.default_workflow = "{latest_workflow}";\n'

    with open(config_path, 'w') as f:
        f.write(config)

    print(f"Đã cài đặt '{latest_workflow}' làm workflow mặc định.")

    # Thêm bước xác minh
    with open(config_path, 'r') as f:
        updated_config = f.read()
    if f'app_config.default_workflow = "{latest_workflow}";' in updated_config:
        print("Xác nhận: Workflow mặc định đã được cài đặt chính xác trong config.js")
    else:
        print("Cảnh báo: Không thể xác nhận việc cài đặt workflow mặc định trong config.js")

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
        for category, links in basic_links.items():
            for link in links:
                filename = os.path.basename(link)
                destination = os.path.join(comfyui_folder, category, filename)
                download_file(link, destination)
        for category, links in user_links.items():
            for link in links:
                filename = os.path.basename(link)
                destination = os.path.join(comfyui_folder, category, filename)
                download_file(link, destination)

        print("Tất cả các mục đã được cài đặt thành công!")

        print("Đang cài đặt workflow mặc định...")
        setup_default_workflow()

        print("Kiểm tra nội dung của config.js:")
        config_path = os.path.join(comfyui_folder, 'web', 'scripts', 'config.js')
        with open(config_path, 'r') as f:
            print(f.read())

        print("Liệt kê các file trong thư mục workflow:")
        workflow_folder = os.path.join(comfyui_folder, 'web', 'workflows')
        print(os.listdir(workflow_folder))

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
