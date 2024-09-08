# ----------------------------------------------------
# KẾT NỐI GOOGLE DRIVE VÀ CẤU HÌNH BAN ĐẦU
# ----------------------------------------------------
from google.colab import drive
import os
import datetime
import requests
from bs4 import BeautifulSoup
import json
from concurrent.futures import ThreadPoolExecutor
import subprocess
from ipywidgets import (Dropdown, Text, Button, VBox, HBox, Checkbox,
    IntSlider, Output, Label, HTML, GridspecLayout, Tab)
from IPython.display import display, clear_output
import logging
from tqdm.notebook import tqdm
import shutil

# Cấu hình logging
logging.basicConfig(filename='comfyui_setup.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Phiên bản hiện tại của DUCNOTE
DUCNOTE_VERSION = "1.3"  # Cập nhật phiên bản

# Mount Google Drive tự động
def mount_google_drive():
    """Kết nối Google Drive."""
    if not os.path.exists('/content/drive'):
        try:
            drive.mount('/content/drive')
            logging.info("Google Drive đã được kết nối.")
            update_output("Google Drive đã được kết nối.")
        except Exception as e:
            logging.error(f"Lỗi khi kết nối Google Drive: {e}")
            display_error(f"Lỗi khi kết nối Google Drive: {e}")
    else:
        logging.info("Google Drive đã được kết nối.")
        update_output("Google Drive đã được kết nối.")

mount_google_drive()

# ----------------------------------------------------
# CẤU HÌNH
# ----------------------------------------------------
google_drive_root_path = '/content/drive/MyDrive'
comfyui_folder_name = ""
comfyui_path_drive = ""
comfyui_github_url = "https://github.com/comfyanonymous/ComfyUI"
config_file = "comfyui_config.json"
ducnote_script_url = (
    "https://github.com/BigKoka/BigKoka/blob/main/ComfyUI-Setup.py"  # Thay thế bằng URL script DUCNOTE của bạn
)

download_categories = {
    "models/checkpoints": "Model Checkpoints",
    "models/controlnet": "ControlNet Models",
    "custom_nodes": "Custom Nodes",
    "models/lora": "Lora Models",
    "models/vae": "VAE Models",
}

dependencies = {
    "ControlNet Models": ["opencv-python", "numpy"],
    "Lora Models": ["torch", "torchvision"],
}

basic_models_nodes = {
    "models/checkpoints": [],
    "models/controlnet": [],
    "custom_nodes": [
    # ...  các  extension  khác  (nếu  có),
    "https://github.com/XLabs-AI/x-flux-comfyui"
  ]
}

# ----------------------------------------------------
# GIAO DIỆN VỚI WIDGETS
# ----------------------------------------------------

# Tab Widget
tab_widget = Tab(layout=Layout(height="600px", width="100%"))
output_general = Output()
output_extensions = Output()
output_models = Output()
tab_widget.children = [output_general, output_extensions, output_models]
tab_widget.set_title(0, "Cài đặt chung")
tab_widget.set_title(1, "Cài đặt Extension")
tab_widget.set_title(2, "Quản lý Model")

# --- Cài đặt chung ---
comfyui_version_input = Dropdown(
    options=["Latest", "Custom Version"],
    description="Phiên bản ComfyUI:",
    value="Latest",
)

custom_version_text = Text(
    value="", placeholder="Nhập branch hoặc tag", description="Branch/Tag:"
)

folder_choice_input = Dropdown(
    options=["Tạo mới", "Sử dụng thư mục có sẵn"],
    description="Lựa chọn thư mục:",
    value="Tạo mới",
)

folder_name_input = Text(
    value="",
    placeholder="Nhập tên thư mục",
    description="Tên thư mục:",
)

save_config_checkbox = Checkbox(
    value=False, description="Lưu cấu hình cho lần sau?"
)

download_speed_slider = IntSlider(
    value=5, min=1, max=10, step=1, description="Số kết nối tải xuống"
)

# --- Cài đặt Extension ---
extension_url_input = Text(
    value="",
    placeholder="Dán URL repository extension",
    description="URL Extension:",
)

install_extension_button = Button(
    description="Cài đặt extension", button_style="info"
)

# --- Quản lý Model ---
category_dropdown = Dropdown(
    options=list(download_categories.keys()),
    description="Loại model/node:",
    value="models/checkpoints",
)

download_link_input = Text(
    value="",
    placeholder="Dán link tải model/custom node...",
    description="Link tải xuống:",
)

add_link_button = Button(description="Thêm link", button_style="info")

# Bảng danh sách model/node
model_table_html = HTML(value="<b>Danh sách model/node đã thêm:</b><br>")
model_table_vbox = VBox([model_table_html])

# Output cho thông báo và lỗi
output_area = Output()
error_output_area = Output()

# --- Sắp xếp giao diện ---
with output_general:
    display(
        comfyui_version_input,
        custom_version_text,
        folder_choice_input,
        folder_name_input,
        save_config_checkbox,
        download_speed_slider,
        output_area,
        error_output_area,
    )

with output_extensions:
    display(extension_url_input, install_extension_button)

with output_models:
    display(
        category_dropdown, download_link_input, add_link_button, model_table_vbox
    )

display(tab_widget)

# ----------------------------------------------------
# HÀM HỖ TRỢ
# ----------------------------------------------------

def update_output(message):
    """Cập nhật message vào output_area."""
    with output_area:
        print(message)


def display_error(message):
    """Hiển thị lỗi trên error_output_area."""
    with error_output_area:
        clear_output()
        print(f"LỖI: {message}")


def check_comfyui_version():
    """Kiểm tra phiên bản ComfyUI mới nhất trên GitHub."""
    try:
        update_output("Đang kiểm tra phiên bản ComfyUI mới nhất...")
        response = requests.get(f"{comfyui_github_url}/releases/latest")
        soup = BeautifulSoup(response.content, "html.parser")
        version = soup.find("span", class_="ml-1").text.strip()
        logging.info(f"Phiên bản ComfyUI mới nhất: {version}")
        update_output(f"Phiên bản ComfyUI mới nhất: {version}")
        return version
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra phiên bản: {e}")
        display_error(f"Lỗi khi kiểm tra phiên bản: {e}")
        return None


def validate_link(link):
    """Kiểm tra liên kết có hợp lệ không."""
    try:
        response = requests.head(link)
        return response.status_code == 200
    except Exception:
        return False

def check_file_on_drive(filename, category_path):
    """Kiểm tra xem file đã tồn tại trong thư mục tương ứng trên Google Drive."""
    if category_path == "custom_nodes":
        save_dir = os.path.join(comfyui_path_drive, "custom_nodes")
    else:
        save_dir = os.path.join(comfyui_path_drive, category_path)
    file_path = os.path.join(save_dir, filename)
    return os.path.exists(file_path)

def install_aria2c():
    """Cài đặt aria2c trên Google Colab."""
    try:
        update_output("Đang cài đặt aria2c...")
        subprocess.run(
            ["apt", "update"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        subprocess.run(
            ["apt", "install", "-y", "aria2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        update_output("Cài đặt aria2c thành công.")
        logging.info("Cài đặt aria2c thành công.")
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt aria2c: {e}")
        display_error(f"Lỗi khi cài đặt aria2c: {e}")

def download_file(link, save_path, pbar=None):
    """Tải file từ liên kết, kiểm tra file đã tồn tại."""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(save_path):
            update_output(f"File đã tồn tại: {save_path}, bỏ qua tải xuống.")
            logging.info(f"File đã tồn tại: {save_path}, bỏ qua tải xuống.")
            if pbar:
                pbar.update(1)  # Cập nhật progress bar
            return f"File đã tồn tại: {save_path}"

        # Kiểm tra xem aria2c đã được cài đặt chưa
        try:
            subprocess.run(
                ["aria2c", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            use_aria2c = True
        except FileNotFoundError:
            use_aria2c = False

        if use_aria2c:
            cmd = [
                "aria2c",
                link,
                "-d",
                os.path.dirname(save_path),
                "-o",
                os.path.basename(save_path),
                "-x",
                str(download_speed_slider.value),
                "-s",
                str(download_speed_slider.value),
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pbar:
                pbar.update(1)
        else:
            os.system(f"gdown --progress bar {link} -O {save_path}")
            if pbar:
                pbar.update(1)

        logging.info(f"Tải thành công: {link}")
        return f"Tải thành công: {link}"

    except Exception as e:
        logging.error(f"Lỗi khi tải {link}: {e}")
        return f"Lỗi khi tải {link}: {e}


def install_library_if_needed(library):
    """Cài đặt thư viện nếu chưa có."""
    try:
        update_output(f"Đang cài đặt thư viện {library}...")
        subprocess.run(
            ["pip", "install", library], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info(f"Thư viện {library} đã được cài đặt.")
        update_output(f"Cài đặt {library} thành công.")
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt thư viện {library}: {e}")
        display_error(f"Lỗi khi cài đặt thư viện {library}: {e}")


def install_dependencies():
    """Cài đặt các thư viện phụ thuộc cần thiết."""
    required_libs = [
        "torch",
        "torchvision",
        "opencv-python",
        "numpy",
        "gdown",
        "ipywidgets",
        "tqdm",
        "requests",
        "beautifulsoup4",
    ]
    for lib in required_libs:
        install_library_if_needed(lib)

def download_files_concurrently(download_links, max_workers):
    """Tải các file, ưu tiên cài đặt từ Google Drive nếu có."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for category_path, links in download_links.items():
            if links:
                update_output(
                    f"Đang tải {download_categories[category_path]}..."
                )
                with tqdm(
                    total=len(links),
                    desc=f"Tải {download_categories[category_path]}",
                ) as pbar:
                    for link in links:
                        filename = os.path.basename(link)
                        
                        # Kiểm tra file đã tồn tại trong Drive chưa
                        if check_file_on_drive(filename, category_path):
                            update_output(f"File '{filename}' đã tồn tại trong Google Drive, bỏ qua tải xuống.")
                            pbar.update(1)  
                            continue # Bỏ qua file hiện tại, tiếp tục với file tiếp theo
                        
                        # Nếu file chưa tồn tại, tải xuống
                        if category_path == "custom_nodes":
                            save_dir = os.path.join(comfyui_path_drive, "custom_nodes")
                        else:
                            save_dir = os.path.join(comfyui_path_drive, category_path)
                        
                        save_path = os.path.join(save_dir, filename)
                        
                        future = executor.submit(download_file, link, save_path, pbar)
                        futures.append(future)
                    # ... (Xử lý kết quả tải xuống)

def create_or_use_folder():
    """Tạo hoặc kiểm tra thư mục để cài đặt ComfyUI."""
    global comfyui_folder_name, comfyui_path_drive
    if folder_choice_input.value == "Tạo mới":
        comfyui_folder_name = (
            "ComfyUI_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        comfyui_path_drive = os.path.join(
            google_drive_root_path, comfyui_folder_name
        )
        os.makedirs(comfyui_path_drive, exist_ok=True)
        logging.info(f"Đã tạo thư mục mới: {comfyui_folder_name}")
        update_output(f"Đã tạo thư mục mới: {comfyui_folder_name}")
    elif folder_choice_input.value == "Sử dụng thư mục có sẵn":
        if not folder_name_input.value.strip():
            display_error("Vui lòng nhập tên thư mục có sẵn.")
            return False
        comfyui_folder_name = folder_name_input.value
        comfyui_path_drive = os.path.join(
            google_drive_root_path, comfyui_folder_name
        )
        if not os.path.exists(comfyui_path_drive):
            display_error(
                f"Thư mục {comfyui_folder_name} không tồn tại. Vui lòng kiểm tra lại."
            )
            return False
    return True


def clone_comfyui_repo():
    """Clone hoặc pull ComfyUI từ GitHub."""
    try:
        update_output(
            f"Đang cài đặt ComfyUI vào thư mục {comfyui_path_drive}..."
        )
        if not os.path.exists(comfyui_path_drive):
            os.makedirs(comfyui_path_drive, exist_ok=True)

        if os.listdir(comfyui_path_drive):
            update_output(
                "ComfyUI đã được cài đặt. Đang kiểm tra và cập nhật phiên bản mới nhất..."
            )
            logging.info(
                "ComfyUI đã được cài đặt. Kiểm tra và cập nhật phiên bản mới nhất."
            )
            process = subprocess.run(
                ["git", "pull"],
                cwd=comfyui_path_drive,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info(process.stdout)
            logging.error(process.stderr)
        else:
            logging.info(f"Clone ComfyUI vào thư mục {comfyui_path_drive}")
            process = subprocess.run(
                ["git", "clone", comfyui_github_url, comfyui_path_drive],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info(process.stdout)
            logging.error(process.stderr)
        update_output("Cài đặt ComfyUI thành công.")
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt ComfyUI: {e}")
        display_error(f"Lỗi khi cài đặt ComfyUI: {e}")


def install_extension(ext_url):
    """Cài đặt extension từ URL, kiểm tra đã tồn tại chưa."""
    try:
        ext_name = os.path.basename(ext_url).split(".")[0]
        save_path = os.path.join(comfyui_path_drive, "custom_nodes", ext_name)

        # Kiểm tra thư mục extension đã tồn tại chưa
        if os.path.exists(save_path):
            update_output(f"Extension đã tồn tại: {ext_name}, bỏ qua cài đặt.")
            logging.info(f"Extension đã tồn tại: {ext_name}, bỏ qua cài đặt.")
            return

        update_output(f"Đang cài đặt extension từ: {ext_url}...")
        process = subprocess.run(
            [
                "git",
                "clone",
                ext_url,
                save_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logging.info(process.stdout)
        if process.returncode == 0:
            update_output(f"Extension {ext_name} đã được cài đặt.")
        else:
            logging.error(f"Lỗi khi cài đặt extension {ext_name}: {process.stderr}")
            display_error(f"Lỗi khi cài đặt extension {ext_name}.")
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt extension: {e}")
        display_error(f"Lỗi khi cài đặt extension: {e}")


def start_comfyui():
    """Khởi chạy ComfyUI."""
    try:
        update_output("Đang khởi chạy ComfyUI...")
        logging.info("Khởi chạy ComfyUI...")
        subprocess.run(["python", "main.py"], cwd=comfyui_path_drive)
        update_output("ComfyUI đã được khởi chạy.")
        logging.info("ComfyUI đã được khởi chạy.")
    except Exception as e:
        logging.error(f"Lỗi khi khởi chạy ComfyUI: {e}")
        display_error(f"Lỗi khi khởi chạy ComfyUI: {e}")


def save_config():
    """Lưu cấu hình của người dùng."""
    try:
        config = {
            "comfyui_version": comfyui_version_input.value,
            "custom_version": custom_version_text.value,
            "folder_choice": folder_choice_input.value,
            "folder_name": folder_name_input.value,
            "save_config": save_config_checkbox.value,
            "download_speed": download_speed_slider.value,
            "models_nodes": basic_models_nodes,  # Lưu danh sách models/nodes
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        logging.info("Cấu hình đã được lưu.")
        update_output("Đã lưu cấu hình.")
    except Exception as e:
        logging.error(f"Lỗi khi lưu cấu hình: {e}")
        display_error(f"Lỗi khi lưu cấu hình: {e}")


def load_config():
    """Tải cấu hình đã lưu."""
    try:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
            comfyui_version_input.value = config.get("comfyui_version", "Latest")
            custom_version_text.value = config.get("custom_version", "")
            folder_choice_input.value = config.get("folder_choice", "Tạo mới")
            folder_name_input.value = config.get("folder_name", "")
            save_config_checkbox.value = config.get("save_config", False)
            download_speed_slider.value = config.get("download_speed", 5)
            logging.info("Cấu hình đã được tải.")
            update_output("Đã tải cấu hình.")

            # Tải danh sách model/nodes
            global basic_models_nodes
            basic_models_nodes = config.get("models_nodes", basic_models_nodes)
            update_model_table()
        else:
            logging.info("Không tìm thấy cấu hình đã lưu.")
            update_output("Không tìm thấy cấu hình đã lưu.")
    except Exception as e:
        logging.error(f"Lỗi khi tải cấu hình: {e}")
        display_error(f"Lỗi khi tải cấu hình: {e}")


def on_comfyui_version_change(change):
    """Ẩn/hiện custom_version_text."""
    if change["new"] == "Latest":
        custom_version_text.layout.visibility = "hidden"
    else:
        custom_version_text.layout.visibility = "visible"


def on_folder_choice_change(change):
    """Tự động điền folder_name_input."""
    if change["new"] == "Sử dụng thư mục có sẵn":
        folder_name = comfyui_folder_name if comfyui_folder_name else ""
        folder_name_input.value = folder_name


def get_free_space_gb(path="/"):
    """Lấy dung lượng trống (GB) của thư mục được chỉ định."""
    try:
        statvfs = os.statvfs(path)
        return statvfs.f_frsize * statvfs.f_bavail / 1024**3
    except Exception as e:
        logging.error(f"Lỗi khi lấy dung lượng trống: {e}")
        return -1


def on_check_space_button_clicked(b):
    """Hiển thị dung lượng trống của Google Drive."""
    free_space = get_free_space_gb(google_drive_root_path)
    if free_space >= 0:
        update_output(f"Dung lượng trống trên Google Drive: {free_space:.2f} GB")
    else:
        display_error("Lỗi khi lấy dung lượng trống của Google Drive.")


def remove_model_link(category, link):
    """Xóa model link khỏi danh sách và cập nhật giao diện."""
    basic_models_nodes[category].remove(link)
    update_model_table()
    update_output(f"Đã xóa liên kết: {link} khỏi danh sách.")


def update_model_table():
    """Cập nhật bảng danh sách model/node."""
    table_html = "<table><tr><th>Loại</th><th>Link</th><th>Thao tác</th></tr>"
    for category, links in basic_models_nodes.items():
        if links:
            for link in links:
                table_html += f"""
                    <tr>
                        <td>{download_categories[category]}</td>
                        <td>{link}</td>
                        <td>
                            <button onclick="remove_model_link('{category}', '{link}')">Xóa</button>
                        </td>
                    </tr>
                """
    table_html += "</table>"
    model_table_html.value = table_html


# ----------------------------------------------------
# SỰ KIỆN KHI NHẤN NÚT
# ----------------------------------------------------


def on_add_link_button_clicked(b):
    """Xử lý khi nhấn nút thêm liên kết tải về."""
    link = download_link_input.value.strip()
    category = category_dropdown.value
    filename = os.path.basename(link)
    if link and validate_link(link):
        # Kiểm tra file đã tồn tại trong Drive chưa
        if check_file_on_drive(filename, category):
            update_output(f"File '{filename}' đã tồn tại trong Google Drive, bỏ qua tải xuống.")
        else:
            basic_models_nodes[category].append(link)
            update_model_table()
            update_output(
                f"Đã thêm liên kết: {link} vào {download_categories[category]}"
            )
        download_link_input.value = ""
    else:
        display_error("Liên kết không hợp lệ. Vui lòng kiểm tra lại.")

def on_install_extension_button_clicked(b):
    """Xử lý khi nhấn nút cài đặt extension."""
    ext_url = extension_url_input.value.strip()
    ext_name = os.path.basename(ext_url).split(".")[0]

    if ext_url:
        # Kiểm tra thư mục extension đã tồn tại trong Drive chưa
        if check_file_on_drive(ext_name, "custom_nodes"):
            update_output(f"Extension '{ext_name}' đã tồn tại trong Google Drive, cài đặt từ Drive.")
            source_path = os.path.join(comfyui_path_drive, "custom_nodes", ext_name) 
            target_path = os.path.join(comfyui_path_drive, "custom_nodes", ext_name)

            if os.path.isfile(source_path) and source_path.endswith(".zip"): # Nếu là file zip
                update_output(f"Extension '{ext_name}' đã tồn tại trong Google Drive, cài đặt từ file ZIP.")
                try:
                    shutil.unpack_archive(source_path, target_path, "zip")
                    update_output(f"Giải nén extension '{ext_name}' thành công.")
                except Exception as e:
                    logging.error(f"Lỗi khi giải nén extension '{ext_name}': {e}")
                    display_error(f"Lỗi khi giải nén extension '{ext_name}'.")
            elif os.path.isdir(source_path): # Nếu là thư mục
                update_output(f"Extension '{ext_name}' đã tồn tại trong Google Drive, cài đặt từ thư mục.")
                try:
                    # Nếu thư mục đích đã tồn tại, xóa thư mục cũ trước khi sao chép
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path)
                    update_output(f"Sao chép extension '{ext_name}' thành công.")
                except Exception as e:
                    logging.error(f"Lỗi khi sao chép extension '{ext_name}': {e}")
                    display_error(f"Lỗi khi sao chép extension '{ext_name}'.") 
            else:
                display_error(f"Không tìm thấy file ZIP hoặc thư mục '{ext_name}' hợp lệ trong Google Drive.") 
        else:
            install_extension(ext_url) 
        extension_url_input.value = ""
    else:
        display_error("Vui lòng nhập URL repository extension.")


def on_start_button_clicked(b):
    """Xử lý khi nhấn nút bắt đầu."""
    clear_output(wait=True)

    # Kiểm tra phiên bản mới
    check_ducnote_version()

    # Tạo hoặc sử dụng thư mục
    if not create_or_use_folder():
        return

    # Cài đặt thư viện
    install_dependencies()

    # Clone hoặc pull repo ComfyUI
    clone_comfyui_repo()

    # Cài đặt aria2c
    install_aria2c()

    # Tải và cài đặt models/nodes
    download_files_concurrently(basic_models_nodes, download_speed_slider.value)

    # Khởi chạy ComfyUI
    start_comfyui()

    # Lưu cấu hình
    if save_config_checkbox.value:
        save_config()


def check_ducnote_version():
    """Kiểm tra phiên bản mới của DUCNOTE."""
    try:
        update_output("Kiểm tra phiên bản DUCNOTE mới...")
        response = requests.get(ducnote_script_url)
        response.raise_for_status()
        latest_script = response.text

        if "DUCNOTE_VERSION =" in latest_script:
            latest_version = latest_script.split("DUCNOTE_VERSION = ")[1].split(
                "\n"
            )[0][1:-1]
            if latest_version != DUCNOTE_VERSION:
                update_output(
                    f"Đã có phiên bản DUCNOTE mới: {latest_version}"
                )
            else:
                update_output("Bạn đang sử dụng phiên bản DUCNOTE mới nhất.")
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra phiên bản DUCNOTE: {e}")
        display_error(f"Lỗi khi kiểm tra phiên bản DUCNOTE: {e}")


# Kết nối sự kiện với các nút
comfyui_version_input.observe(on_comfyui_version_change, "value")
folder_choice_input.observe(on_folder_choice_change, "value")
add_link_button.on_click(on_add_link_button_clicked)
install_extension_button.on_click(on_install_extension_button_clicked)
check_space_button.on_click(on_check_space_button_clicked)
start_button.on_click(on_start_button_clicked)

# ----------------------------------------------------
# TẢI CẤU HÌNH
# ----------------------------------------------------
load_config()
on_comfyui_version_change({"new": comfyui_version_input.value})
