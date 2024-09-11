#@title # ⚙️ 1. Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

#@title # ⚙️ 2. Chọn phiên bản ComfyUI
#@markdown Chọn phiên bản ComfyUI để cài đặt
version = "latest" #@param ["latest", "v1.0", "v1.1", "v1.2"]

#@title # ⌛️ 3. Cài đặt ComfyUI
import os

# Tạo thư mục ComfyUI nếu chưa có
comfyui_folder = '/content/drive/MyDrive/ComfyUI'
if not os.path.exists(comfyui_folder):
    os.makedirs(comfyui_folder)

# Cài đặt phiên bản ComfyUI đã chọn
if version == "latest":
    !git clone https://github.com/comfyanonymous/ComfyUI.git {comfyui_folder}
else:
    !git clone --branch {version} https://github.com/comfyanonymous/ComfyUI.git {comfyui_folder}

# Cài đặt các thư viện phụ thuộc
%cd {comfyui_folder}
!pip install -r requirements.txt

# Cài đặt ngrok
!pip install pyngrok

#@title # 🚀 4. Khởi chạy ComfyUI
import subprocess
import time
from pyngrok import ngrok

# Khởi chạy ComfyUI
comfyui_process = subprocess.Popen(['python', 'main.py'], cwd=comfyui_folder)

# Xác thực ngrok
ngrok.set_auth_token("2lsH20LJlGepInz2kHp6BVqa564_BeHWgKMoK2XXsPQrZbRh")

# Tạo link truy cập bằng ngrok với subdomain cụ thể
time.sleep(5)  # Đợi một chút để ComfyUI khởi động
ngrok_tunnel = ngrok.connect(8188)
ngrok_url = ngrok_tunnel.public_url
print(f"Truy cập ComfyUI tại: {ngrok_url}")

# Hiển thị mật khẩu và link truy cập
ngrok_password = ngrok_url.split('//')[1].split('.')[0]
print("Khởi chạy ngrok Server")
print(f"Mật khẩu cho ngrok là: {ngrok_password}")
print(f"your url is: {ngrok_url}")
