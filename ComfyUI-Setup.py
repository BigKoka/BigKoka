# @title
import os
import subprocess
import time
import requests
import re
import shutil
from google.colab import drive
from google.colab import output
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

# Cài đặt ipywidgets nếu chưa có
!pip install ipywidgets -q

# Thiết lập các biến và cấu trúc dữ liệu
comfyui_folder = '/content/drive/MyDrive/ComfyUI'
version = "latest"

basic_links = {
    'models': [ ],
    'extensions': [ ],
    'custom_nodes': [
        'https://github.com/florestefano1975/comfyui-portrait-master',
        'https://github.com/giriss/comfy-image-saver',
        'https://github.com/XLabs-AI/x-flux-comfyui',
        'https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes'

    ],
    'loras': [ ],
    'vae': [ ]
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
    for folder in ['models', 'extensions', 'custom_nodes', 'loras', 'vae', 'controlnet', 'embeddings']:
        os.makedirs(os.path.join(comfyui_folder, folder), exist_ok=True)

def download_file(url, destination):
    response = requests.get(url)
    with open(destination, 'wb') as file:
        file.write(response.content)

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

# Hàm xử lý sự kiện
def add_link(b):
    category = category_dropdown.value
    link = link_input.value
    if link:
        user_links[category].append(link)
        link_input.value = ''
        update_link_list()

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
                print(f'Đã tải xuống {filename} vào {destination}')
        for category, links in user_links.items():
            for link in links:
                filename = os.path.basename(link)
                destination = os.path.join(comfyui_folder, category, filename)
                download_file(link, destination)
                print(f'Đã tải xuống {filename} vào {destination}')
        
        print("Tất cả các mục đã được cài đặt thành công!")
        
        print("Đang khởi động ComfyUI...")
        os.chdir(comfyui_folder)
        comfyui_process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("Đang đợi ComfyUI khởi động...")
        timeout = 300  # 5 phút
        start_time = time.time()
        while not is_comfyui_ready():
            if time.time() - start_time > timeout:
                print("ComfyUI không khởi động được trong thời gian chờ. Đang in logs...")
                output, error = comfyui_process.communicate()
                print("Output:", output.decode())
                print("Error:", error.decode())
                return
            time.sleep(5)
            print(".", end="", flush=True)

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
    links_html = '<ul>'
    for category in basic_links.keys():
        for link in basic_links[category] + user_links[category]:
            links_html += f'<li>{link} <button onclick="remove_link(\'{category}\', \'{link}\')">Remove</button></li>'
    links_html += '</ul>'
    link_list.value = links_html

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
