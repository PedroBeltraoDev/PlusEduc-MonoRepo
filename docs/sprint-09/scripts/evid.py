"""Helpers para capturar evidências da interface (Chrome headless controlado por Selenium)."""
import os, time, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont

UI = 'http://127.0.0.1:5183'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'evidencias')
PW = os.environ['PLUSEDUC_EVAL_PASSWORD']
os.makedirs(OUT, exist_ok=True)
MANIFEST = []
DOWNLOADS = os.path.join(os.environ.get('TEMP', '.'), 'pluseduc_downloads')


def make_driver(width=1366, height=860):
    o = Options()
    o.add_argument('--headless=new')
    o.add_argument(f'--window-size={width},{height}')
    o.add_argument('--lang=pt-BR')
    o.add_argument('--hide-scrollbars')
    os.makedirs(DOWNLOADS, exist_ok=True)
    o.add_experimental_option('prefs', {'download.default_directory': DOWNLOADS, 'download.prompt_for_download': False})
    d = webdriver.Chrome(options=o)
    d.implicitly_wait(0)
    return d


def font(size):
    for name in ('arial.ttf', 'segoeui.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def shot(d, name, caption, full=False):
    """Salva a captura com uma faixa superior (endereço atual + legenda), pois o modo headless não mostra a barra de endereço."""
    time.sleep(0.8)
    path = os.path.join(OUT, f'{name}.png')
    if full:
        h = d.execute_script('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')
        d.set_window_size(d.get_window_size()['width'], min(h + 20, 3000))
        time.sleep(0.6)
    d.save_screenshot(path)
    if full:
        d.set_window_size(1366, 860)
    img = Image.open(path).convert('RGB')
    bar_h = 54
    out = Image.new('RGB', (img.width, img.height + bar_h), (30, 41, 59))
    out.paste(img, (0, bar_h))
    dr = ImageDraw.Draw(out)
    url = d.current_url
    dr.text((12, 7), url, fill=(147, 197, 253), font=font(15))
    dr.text((12, 29), caption, fill=(255, 255, 255), font=font(15))
    out.save(path)
    MANIFEST.append({'arquivo': f'{name}.png', 'legenda': caption, 'url': url, 'hora': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')})
    print('captura', name, '|', url)


def wait(d, css, timeout=15):
    return WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))


def xp(d, xpath, timeout=15):
    return WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))


def clear_session(d):
    d.get(UI + '/login')
    d.execute_script('localStorage.clear(); sessionStorage.clear();')


def login_ui(d, email, password=PW, expect_path=None):
    clear_session(d)
    d.get(UI + '/login')
    wait(d, 'input[type=email], input[type=text]')
    inputs = d.find_elements(By.CSS_SELECTOR, 'input')
    inputs[0].send_keys(email)
    inputs[1].send_keys(password)
    xp(d, "//button[contains(., 'Entrar')]").click()
    if expect_path:
        WebDriverWait(d, 15).until(lambda x: expect_path in x.current_url)
    time.sleep(1.5)


def goto(d, path, settle=1.8):
    d.get(UI + path)
    time.sleep(settle)
