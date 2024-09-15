# @title Cài đặt và Chạy ComfyUI trên Google Colab

!pip install ipywidgets tqdm gitpython requests -q

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
from tqdm.notebook import tqdm
from urllib.parse import urlparse
import git
from google.colab import output as colab_output

# Cấu hình
COMFYUI_FOLDER = '/content/drive/MyDrive/ComfyUI'
VERSION = "latest"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"

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

user_links = {category: [] for category in BASIC_LINKS.keys()}

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)
    cmd_output, error = process.communicate()
    if process.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Output: {output}")
        print(f"Error: {error}")
        return False
    return True

def create_folders():
    for folder in BASIC_LINKS.keys():
        os.makedirs(os.path.join(COMFYUI_FOLDER, folder), exist_ok=True)

def is_git_repo(url):
    return url.endswith('.git') or ('github.com' in url and not url.endswith('.json'))

def clone_or_pull_repo(url, destination):
    try:
        if os.path.exists(destination):
            print(f"Updating existing repository: {destination}")
            repo = git.Repo(destination)
            repo.remotes.origin.pull()
        else:
            print(f"Cloning repository: {url}")
            git.Repo.clone_from(url, destination)
        print(f"Successfully updated/cloned repository: {url}")
        return True
    except git.GitCommandError as e:
        print(f"Git operation failed for {url}: {str(e)}")
        return False

def download_file(url, destination):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(destination), exist_ok=True)

        if os.path.exists(destination):
            print(f"File already exists: {destination}. Skipping download.")
            return True

        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192

        with open(destination, 'wb') as file, tqdm(
            desc=os.path.basename(destination),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for data in response.iter_content(block_size):
                size = file.write(data)
                progress_bar.update(size)

        print(f"Downloaded {url} to {destination}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def download_json(url, destination):
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_content = response.json()
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w') as f:
            json.dump(json_content, f, indent=2)
        print(f"Downloaded JSON from {url} to {destination}")
        return json_content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading from {url}: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON from {url}: {str(e)}")
        print("Received content:")
        print(response.text[:500])
    except Exception as e:
        print(f"Unexpected error processing {url}: {str(e)}")
    return None

def is_comfyui_ready():
    try:
        response = requests.get('http://localhost:8188', timeout=5)
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

def add_link(b):
    category = category_dropdown.value
    link = link_input.value.strip()
    if link:
        if link in BASIC_LINKS[category] or any(link in user_links[cat] for cat in user_links):
            with status_output:
                print(f"Link '{link}' already exists in the list.")
        else:
            user_links[category].append(link)
            link_input.value = ''
            update_link_list()
            with status_output:
                print(f"Added link '{link}' to {category} list.")

def remove_link(category, link):
    if link in user_links[category]:
        user_links[category].remove(link)
    elif link in BASIC_LINKS[category]:
        BASIC_LINKS[category].remove(link)
    update_link_list()

def install_all(b):
    status_output.clear_output()
    with status_output:
        print("Mounting Google Drive...")
        drive.mount('/content/drive')

        print("Installing cloudflared...")
        if not run_command(f"wget -q -c {CLOUDFLARED_URL} && dpkg -i cloudflared-linux-amd64.deb"):
            print("Failed to install cloudflared. Continuing without it.")

        print(f"Installing/updating ComfyUI version {VERSION}...")
        if os.path.exists(COMFYUI_FOLDER):
            print("ComfyUI folder exists. Updating...")
            os.chdir(COMFYUI_FOLDER)
            if not run_command("git pull"):
                print("Failed to update ComfyUI. Reinstalling...")
                os.chdir('..')
                shutil.rmtree(COMFYUI_FOLDER)
                os.makedirs(COMFYUI_FOLDER)
        else:
            os.makedirs(COMFYUI_FOLDER)

        if not os.path.exists(os.path.join(COMFYUI_FOLDER, '.git')):
            clone_command = f"git clone {'--branch ' + VERSION if VERSION != 'latest' else ''} https://github.com/comfyanonymous/ComfyUI.git {COMFYUI_FOLDER}"
            if not run_command(clone_command):
                print("Failed to clone ComfyUI repository. Check your internet connection and try again.")
                return

        print("Installing dependencies...")
        os.chdir(COMFYUI_FOLDER)
        if not run_command("pip install -r requirements.txt"):
            print("Failed to install dependencies. Check requirements.txt and try again.")
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

        print("All items installed successfully!")

        print("Starting ComfyUI...")
        os.chdir(COMFYUI_FOLDER)
        comfyui_process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("Waiting for ComfyUI to start...")
        timeout = 300  # 5 minutes
        start_time = time.time()
        with tqdm(total=timeout, desc="Starting ComfyUI", unit="seconds") as pbar:
            while not is_comfyui_ready():
                if time.time() - start_time > timeout:
                    print("ComfyUI failed to start within the timeout period. Printing logs...")
                    output, error = comfyui_process.communicate()
                    print("Output:", output.decode())
                    print("Error:", error.decode())
                    return
                time.sleep(1)
                pbar.update(1)

        print("\nComfyUI is ready!")

        print("Starting Cloudflared and getting URL...")
        url = get_cloudflared_url()
        if url:
            print(f"ComfyUI is accessible at: {url}")
        else:
            print("Failed to get URL from Cloudflared. Trying alternative methods...")

        print("Checking Google Colab port forwarding...")
        colab_output.serve_kernel_port_as_window(8188)
        print("Please check the URL created by Colab above.")

        print("If you still don't see a URL, check the 'Tools' > 'Ports' tab in Google Colab to find the access URL for port 8188.")

def update_link_list():
    table_html = '''
    <table style="width:100%; border-collapse: collapse;">
    <tr>
    <th style="border: 1px solid black; padding: 5px;">Category</th>
    <th style="border: 1px solid black; padding: 5px;">Link</th>
    <th style="border: 1px solid black; padding: 5px;">Remove</th>
    </tr>
    '''
    for category in BASIC_LINKS.keys():
        for link in BASIC_LINKS[category] + user_links[category]:
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

# Create widgets
category_dropdown = widgets.Dropdown(options=list(BASIC_LINKS.keys()), description='Category:')
link_input = widgets.Text(description='Link:')
add_button = widgets.Button(description='Add Link')
install_all_button = widgets.Button(description='Install All')
link_list = widgets.HTML()
status_output = widgets.Output()

# Set up event handling
add_button.on_click(add_link)
install_all_button.on_click(install_all)

# Create layout
app = widgets.VBox([
    widgets.HBox([category_dropdown, link_input, add_button]),
    link_list,
    install_all_button,
    status_output
])

# JavaScript to handle Remove button
js = """
<script>
function remove_link(category, link) {
    google.colab.kernel.invokeFunction('notebook.remove_link', [category, link], {});
}
</script>
"""
display(HTML(js))

# Register Python function to be called from JavaScript
output.register_callback('notebook.remove_link', remove_link)

# Display the application
display(app)

# Update initial link list
update_link_list()
