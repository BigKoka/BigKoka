# @title
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
from ipywidgets import (
    Dropdown,
    Text,
    Button,
    VBox,
    HBox,
    Checkbox,
    IntSlider,
    Output,
    Label,
    HTML,
    GridspecLayout,
    Layout,
)
from IPython.display import display, clear_output
import logging
from tqdm.notebook import tqdm
import shutil
from IPython.display import Javascript
from google.colab import output
from ipywidgets import Button, HBox, VBox, HTML


# Cấu hình logging
logging.basicConfig(
    filename="comfyui_setup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Phiên bản hiện tại của DUCNOTE
DUCNOTE_VERSION = "1.5"  # Cập nhật phiên bản
config_file = "comfyui_config.json"
comfyui_github_url = "https://github.com/comfyanonymous/ComfyUI"
# ----------------------------------------------------
# KẾT NỐI GOOGLE DRIVE VÀ CẤU HÌNH BAN ĐẦU
# ----------------------------------------------------
from google.colab import drive
import os

# Kiểm tra xem drive đã được mount chưa
if not os.path.exists('/content/drive'):
  drive.mount('/content/drive')
else:
  print("Google Drive đã được kết nối.")

google_drive_root_path = "/content/drive/My Drive" 
import datetime

# Lưu trữ các model/node cần tải theo loại
basic_models_nodes = {
    "models/checkpoints": [],
    "models/vae": [],
    "models/embeddings": [],
    "models/hypernetworks": [],
    "models/lora": [],
    "models/controlnet": [],
    "custom_nodes": [
        "https://github.com/XLabs-AI/x-flux-comfyui",
        "https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes",
    ],
}

download_categories = {
    "models/checkpoints": "Checkpoints",
    "models/vae": "VAEs",
    "models/embeddings": "Embeddings",
    "models/hypernetworks": "Hypernetworks",
    "models/lora": "Loras",
    "models/controlnet": "ControlNets",
    "custom_nodes": "Custom Nodes",
}

# ----------------------------------------------------
# HÀM HỖ TRỢ
# ----------------------------------------------------
def update_output(message, output_area):
    """Cập nhật message vào output_area."""
    with output_area:
        print(message)

def display_error(message, error_output_area):
    """Hiển thị lỗi trên error_output_area."""
    with error_output_area:
        clear_output()
        print(f"LỖI: {message}")

def check_comfyui_version(output_area, error_output_area):
    """Kiểm tra phiên bản ComfyUI mới nhất trên GitHub."""
    try:
        update_output("Đang kiểm tra phiên bản ComfyUI mới nhất...", output_area)
        response = requests.get(f"{comfyui_github_url}/releases/latest")
        soup = BeautifulSoup(response.content, "html.parser")
        version = soup.find("span", class_="ml-1").text.strip()
        logging.info(f"Phiên bản ComfyUI mới nhất: {version}")
        update_output(f"Phiên bản ComfyUI mới nhất: {version}", output_area)
        return version
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra phiên bản: {e}")
        display_error(f"Lỗi khi kiểm tra phiên bản: {e}", error_output_area)
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

def install_aria2c(output_area, error_output_area):
    """Cài đặt aria2c trên Google Colab."""
    try:
        update_output("Đang cài đặt aria2c...", output_area)
        subprocess.run(["apt", "update"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["apt", "install", "-y", "aria2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        update_output("Cài đặt aria2c thành công.", output_area)
        logging.info("Cài đặt aria2c thành công.")
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt aria2c: {e}")
        display_error(f"Lỗi khi cài đặt aria2c: {e}", error_output_area)

def download_file(link, save_path, pbar=None):
    """Tải file từ liên kết, kiểm tra file đã tồn tại."""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(save_path):
            update_output(f"File đã tồn tại: {save_path}, bỏ qua tải xuống.", output_area)
            logging.info(f"File đã tồn tại: {save_path}, bỏ qua tải xuống.")
            if pbar:
                pbar.update(1)  # Cập nhật progress bar
            return f"File đã tồn tại: {save_path}"

        # Kiểm tra xem aria2c đã được cài đặt chưa
        try:
            subprocess.run(["aria2c", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        return f"Lỗi khi tải {link}: {e}"

def install_library_if_needed(library, output_area, error_output_area):
    """Cài đặt thư viện nếu chưa có."""
    try:
        update_output(f"Đang cài đặt thư viện {library}...", output_area)
        subprocess.run(["pip", "install", library], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Thư viện {library} đã được cài đặt.")
        update_output(f"Cài đặt {library} thành công.", output_area)
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt thư viện {library}: {e}")
        display_error(f"Lỗi khi cài đặt thư viện {library}: {e}", error_output_area)

def install_dependencies(output_area, error_output_area):
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
        install_library_if_needed(lib, output_area, error_output_area)

def download_files_concurrently(download_links, max_workers, output_area, error_output_area):
    """Tải các file, ưu tiên cài đặt từ Google Drive nếu có."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for category_path, links in download_links.items():
            if links:
                update_output(f"Đang tải {download_categories[category_path]}...", output_area)
                with tqdm(total=len(links), desc=f"Tải {download_categories[category_path]}") as pbar:
                    for link in links:
                        filename = os.path.basename(link)

                        # Kiểm tra file đã tồn tại trong Drive chưa
                        if check_file_on_drive(filename, category_path):
                            update_output(
                                f"File '{filename}' đã tồn tại trong Google Drive, bỏ qua tải xuống.",
                                output_area,
                            )
                            pbar.update(1)
                            continue  # Bỏ qua file hiện tại, tiếp tục với file tiếp theo

                        # Nếu file chưa tồn tại, tải xuống
                        if category_path == "custom_nodes":
                            save_dir = os.path.join(comfyui_path_drive, "custom_nodes")
                        else:
                            save_dir = os.path.join(comfyui_path_drive, category_path)

                        save_path = os.path.join(save_dir, filename)

                        future = executor.submit(download_file, link, save_path, pbar)
                        futures.append(future)

def create_or_use_folder(output_area, error_output_area, folder_name_input, general_settings_box):
    """Tạo hoặc kiểm tra thư mục để cài đặt ComfyUI."""
    global comfyui_folder_name, comfyui_path_drive
    if folder_choice_input.value == "Tạo mới":
        comfyui_folder_name = "ComfyUI_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        comfyui_path_drive = os.path.join(google_drive_root_path, comfyui_folder_name)
        os.makedirs(comfyui_path_drive, exist_ok=True)
        logging.info(f"Đã tạo thư mục mới: {comfyui_folder_name}")
        update_output(f"Đã tạo thư mục mới: {comfyui_folder_name}", output_area)
    elif folder_choice_input.value == "Sử dụng thư mục có sẵn":
        if not folder_name_input.value.strip():
            display_error("Vui lòng nhập tên thư mục có sẵn.", error_output_area)
            return False
        comfyui_folder_name = folder_name_input.value
        comfyui_path_drive = os.path.join(google_drive_root_path, comfyui_folder_name)
        if not os.path.exists(comfyui_path_drive):
            display_error(f"Thư mục {comfyui_folder_name} không tồn tại. Vui lòng kiểm tra lại.", error_output_area)
            return False
    return True

def clone_comfyui_repo(output_area, error_output_area):
    try:
        update_output(f"Đang cài đặt ComfyUI vào thư mục {comfyui_path_drive}...", output_area)
        if not os.path.exists(comfyui_path_drive):
            os.makedirs(comfyui_path_drive, exist_ok=True)

        if os.listdir(comfyui_path_drive):
            update_output(
                "ComfyUI đã được cài đặt. Đang kiểm tra và cập nhật phiên bản mới nhất...",
                output_area,
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
        
        # Cài đặt dependencies
        update_output("Đang cài đặt các thư viện phụ thuộc...", output_area)
        requirements_file = os.path.join(comfyui_path_drive, "requirements.txt")
        if os.path.exists(requirements_file):
            subprocess.run(
                ["pip", "install", "-r", requirements_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        
        # Cài đặt thêm torchsde
        subprocess.run(
            ["pip", "install", "torchsde"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        update_output("Cài đặt ComfyUI và các thư viện phụ thuộc thành công.", output_area)
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt ComfyUI: {e}")
        display_error(f"Lỗi khi cài đặt ComfyUI: {e}", error_output_area)

def install_additional_dependencies(output_area, error_output_area):
    try:
        update_output("Đang cài đặt các thư viện bổ sung...", output_area)
        additional_dependencies = [
            "torch", "torchvision", "torchaudio", "torchsde",
            "opencv-python", "pillow", "einops", "transformers", "safetensors",
            "aiohttp", "accelerate", "pyyaml", "scipy"
        ]
        for dep in additional_dependencies:
            subprocess.run(
                ["pip", "install", dep],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        update_output("Cài đặt các thư viện bổ sung thành công.", output_area)
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt các thư viện bổ sung: {e}")
        display_error(f"Lỗi khi cài đặt các thư viện bổ sung: {e}", error_output_area)       

def install_extension(ext_url, output_area, error_output_area):
    """Cài đặt extension từ URL, kiểm tra đã tồn tại chưa."""
    try:
        ext_name = os.path.basename(ext_url).split(".")[0]
        save_path = os.path.join(comfyui_path_drive, "custom_nodes", ext_name)

        # Kiểm tra thư mục extension đã tồn tại chưa
        if os.path.exists(save_path):
            update_output(f"Extension đã tồn tại: {ext_name}, bỏ qua cài đặt.", output_area)
            logging.info(f"Extension đã tồn tại: {ext_name}, bỏ qua cài đặt.")
            return

        update_output(f"Đang cài đặt extension từ: {ext_url}...", output_area)
        process = subprocess.run(
            ["git", "clone", ext_url, save_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logging.info(process.stdout)
        if process.returncode == 0:
            update_output(f"Extension {ext_name} đã được cài đặt.", output_area)
        else:
            logging.error(f"Lỗi khi cài đặt extension {ext_name}: {process.stderr}")
            display_error(f"Lỗi khi cài đặt extension {ext_name}.", error_output_area)
    except Exception as e:
        logging.error(f"Lỗi khi cài đặt extension: {e}")
        display_error(f"Lỗi khi cài đặt extension: {e}", error_output_area)

def start_comfyui(output_area, error_output_area):
    """Khởi chạy ComfyUI."""
    try:
        update_output("Đang khởi chạy ComfyUI...", output_area)
        logging.info("Khởi chạy ComfyUI...")
        subprocess.run(["python", "main.py"], cwd=comfyui_path_drive)
        update_output("ComfyUI đã được khởi chạy.", output_area)
        logging.info("ComfyUI đã được khởi chạy.")
    except Exception as e:
        logging.error(f"Lỗi khi khởi chạy ComfyUI: {e}")
        display_error(f"Lỗi khi khởi chạy ComfyUI: {e}", error_output_area)

def save_config(output_area, error_output_area):
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
        update_output("Đã lưu cấu hình.", output_area)
    except Exception as e:
        logging.error(f"Lỗi khi lưu cấu hình: {e}")
        display_error(f"Lỗi khi lưu cấu hình: {e}", error_output_area)

def load_config(output_area, error_output_area):
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
            update_output("Đã  tải  cấu  hình.", output_area)

            # Tải danh sách model/nodes
            global basic_models_nodes
            basic_models_nodes = config.get("models_nodes", basic_models_nodes)

            # Cập nhật bảng HTML dựa trên basic_models_nodes
            update_model_table()

        else:
            logging.info("Không tìm thấy cấu hình đã lưu.")
            update_output("Không  tìm  thấy  cấu  hình  đã  lưu.", output_area)
    except Exception as e:
        logging.error(f"Lỗi khi tải cấu hình: {e}")
        display_error(f"Lỗi  khi  tải  cấu  hình:  {e}", error_output_area)

def on_comfyui_version_change(change):
    """Ẩn/Hiện custom_version_text."""
    if change["new"] == "Custom Version":
        custom_version_text.layout.visibility = "visible"

        # Tìm vị trí của comfyui_version_input trong danh sách children
        index = general_settings_box.children.index(comfyui_version_input)

        # Nếu custom_version_text chưa có trong danh sách, chèn nó vào vị trí sau comfyui_version_input
        if custom_version_text not in general_settings_box.children:
            children_list = list(general_settings_box.children)
            children_list.insert(index + 1, custom_version_text)
            general_settings_box.children = tuple(children_list)
    else:
        custom_version_text.layout.visibility = "hidden"
        # Xóa custom_version_text khỏi container (nếu có)
        general_settings_box.children = tuple(
            w for w in general_settings_box.children if w != custom_version_text
        )

def on_folder_choice_change(change):
    """Ẩn/Hiện textbox "Tên thư mục có sẵn"."""
    if change["new"] == "Sử dụng thư mục có sẵn":
        folder_name_input.layout.visibility = "visible"

        # Lấy danh sách widgets hiện tại
        children = list(general_settings_box.children)

        # Tìm vị trí của folder_choice_input
        index = children.index(folder_choice_input)

        # Chèn folder_name_input vào vị trí sau folder_choice_input
        children.insert(index + 1, folder_name_input)

        # Cập nhật lại danh sách widgets cho container
        general_settings_box.children = children
    else:
        folder_name_input.layout.visibility = "hidden"

        # Xóa folder_name_input khỏi container (nếu có)
        general_settings_box.children = tuple(
            w for w in general_settings_box.children if w != folder_name_input
        )

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
        update_output(f"Dung lượng trống trên Google Drive: {free_space:.2f}  GB", output_area)
    else:
        display_error("Lỗi  khi  lấy  dung  lượng  trống  của  Google  Drive.", error_output_area)

def update_model_table():
    global basic_models_nodes, model_table_vbox

    table_rows = []
    for category, links in basic_models_nodes.items():
        for link in links:
            category_label = HTML(value=f"<b>{download_categories[category]}</b>")
            link_label = HTML(value=link)
            delete_button = Button(description="Xóa", button_style="danger", layout={'width': 'auto'})
            delete_button.on_click(lambda b, c=category, l=link: remove_model_link(c, l))
            row = HBox([category_label, link_label, delete_button])
            table_rows.append(row)

    if table_rows:
        model_table_vbox.children = tuple([HTML("<b>Danh sách model/node/extension đã thêm:</b>")] + table_rows)
    else:
        model_table_vbox.children = (HTML("<b>Danh sách model/node/extension đã thêm:</b><br>Chưa có mục nào được thêm."),)        

def remove_model_link(category, link):
    global basic_models_nodes
    if category in basic_models_nodes and link in basic_models_nodes[category]:
        basic_models_nodes[category].remove(link)
        update_output(f"Đã xóa liên kết: {link} khỏi danh sách {download_categories[category]}.", output_area)
        update_model_table()
    else:
        update_output(f"Không tìm thấy liên kết: {link} trong danh sách {download_categories[category]}.", output_area)

def on_add_link_button_clicked(b):
    category = category_dropdown.value
    link = download_link_input.value.strip()
    
    if not link:
        display_error("Vui lòng nhập link tải xuống.", error_output_area)
        return
    
    if not validate_link(link):
        display_error("Link không hợp lệ. Vui lòng kiểm tra lại.", error_output_area)
        return
    
    if link not in basic_models_nodes[category]:
        basic_models_nodes[category].append(link)
        update_output(f"Đã thêm link: {link} vào danh sách {download_categories[category]}.", output_area)
        download_link_input.value = ""  # Clear input after adding
        update_model_table()  # Update the table after adding a new link
    else:
        update_output(f"Link: {link} đã tồn tại trong danh sách {download_categories[category]}.", output_area)

# ... các hàm khác ...

def on_start_button_clicked(b):
    try:
        global google_drive_root_path 
        if save_config_checkbox.value:
            save_config(output_area, error_output_area)

        on_check_space_button_clicked(None)  

        if not create_or_use_folder(
            output_area, error_output_area, folder_name_input, general_settings_box
        ):
            return  

        install_dependencies(output_area, error_output_area)
        install_additional_dependencies(output_area, error_output_area)  # Thêm dòng này
        clone_comfyui_repo(output_area, error_output_area)

        for link in basic_models_nodes.get("custom_nodes", []):
            install_extension(link, output_area, error_output_area)

        download_files_concurrently(
            basic_models_nodes, download_speed_slider.value, output_area, error_output_area
        )
        start_comfyui(output_area, error_output_area)

    except Exception as e:
        logging.error(f"Lỗi trong quá trình cài đặt: {e}")
        display_error(f"Đã xảy ra lỗi trong quá trình cài đặt: {e}", error_output_area)      

# ----------------------------------------------------
# GIAO DIỆN VỚI WIDGETS
# ----------------------------------------------------

# Output cho tab Cài đặt Chung
output_general = Output()

# --- Cài đặt chung ---
general_settings_box = VBox()

comfyui_version_label = Label(
    value="Phiên bản ComfyUI: Latest (Phiên bản mới nhất) hoặc Custom Version (Tùy chọn phiên bản)"
)
comfyui_version_input = Dropdown(
    options=["Latest", "Custom Version"], value="Latest"
)

custom_version_text = Text(
    value="",
    placeholder="Ví dụ: dev, feature/new-feature, v1.0.0, v1.1.2...",
)
custom_version_text.layout.visibility = "hidden"

folder_choice_label = Label(value="Lựa chọn thư mục lưu ComfyUI:")
folder_choice_input = Dropdown(
    options=["Tạo mới", "Sử dụng thư mục có sẵn"], value="Tạo mới"
)

folder_name_input = Text(value="", placeholder="Nhập tên thư mục có sẵn")
folder_name_input.layout.visibility = "hidden"

save_config_checkbox = Checkbox(
    value=False, description="Lưu cấu hình cho lần sau?"
)

# --- Quản lý Model và Extension ---
category_dropdown_label = Label(value="Chọn loại model/node/extension:")
category_dropdown = Dropdown(
    options=list(download_categories.keys()),
    value="models/checkpoints",
)

download_link_label = Label(value="Link tải xuống:")
download_link_input = Text(
    value="", placeholder="Dán link tải model/node/extension..."
)

add_link_button = Button(description="Thêm link", button_style="info")

# Bảng danh sách model/node
model_table_vbox = VBox([HTML("<b>Danh sách model/node/extension đã thêm:</b><br>Chưa có mục nào được thêm.")])
# model_table_html = HTML(value="<b>Danh sách model/node/extension đã thêm:</b><br>")
# model_table_vbox = VBox([model_table_html])

# --- Các cài đặt khác ---
check_space_button = Button(description="Kiểm tra dung lượng", button_style="info")
start_button = Button(description="Bắt đầu cài đặt", button_style="success")

download_speed_label = Label(
    value="Chọn số kết nối tải xuống (Sử dụng tải đa luồng cho phép tải nhanh)"
)
download_speed_slider = IntSlider(value=5, min=1, max=10, step=1)

# Output cho thông báo và lỗi
output_area = Output()
error_output_area = Output()

# --- Sắp xếp giao diện ---
with output_general:
    general_settings_box.children = [
        comfyui_version_label,
        comfyui_version_input,
        folder_choice_label,
        folder_choice_input,
        # --- Quản lý Model và Extension ---
        category_dropdown_label,
        category_dropdown,
        download_link_label,
        download_link_input,
        add_link_button,
        model_table_vbox,
        # ---
        save_config_checkbox,
        check_space_button,
        start_button,
        download_speed_label,
        download_speed_slider,
        output_area,
        error_output_area,
    ]
    display(general_settings_box)
    update_model_table()  # Gọi update_model_table() để khởi tạo bảng HTML

# Hiển thị tab Cài đặt Chung
display(output_general)

# Hiển thị bảng model/node

# ----------------------------------------------------
# SỰ KIỆN KHI NHẤN NÚT
# ----------------------------------------------------
comfyui_version_input.observe(on_comfyui_version_change, "value")
folder_choice_input.observe(on_folder_choice_change, "value")
add_link_button.on_click(on_add_link_button_clicked)
check_space_button.on_click(on_check_space_button_clicked)
start_button.on_click(on_start_button_clicked)

# ----------------------------------------------------
# TẢI CẤU HÌNH
# ----------------------------------------------------
load_config(output_area, error_output_area)
on_comfyui_version_change({"new": comfyui_version_input.value})
