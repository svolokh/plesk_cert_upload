from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
import chromedriver_binary
import time
import os.path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--plesk_url', required=True)
parser.add_argument('--plesk_username', required=True)
parser.add_argument('--plesk_password', required=True)
parser.add_argument('--plesk_site_id', required=True)
parser.add_argument('--privkey', required=True)
parser.add_argument('--cert', required=True)
args = parser.parse_args()

PLESK_URL = args.plesk_url
PLESK_USERNAME = args.plesk_username
PLESK_PASSWORD = args.plesk_password
SITE_ID = args.plesk_site_id

CERT_PREFIX = 'LECert'

privkey_pem = os.path.abspath(args.privkey) 
cert_pem = os.path.abspath(args.cert)

chrome_options = Options()
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(options=chrome_options)

def plesk_login():
    driver.get(PLESK_URL)
    username_elem = driver.find_element(By.ID, 'login_name')
    password_elem = driver.find_element(By.ID, 'passwd')
    submit_elem = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"][name="send"]')
    username_elem.clear()
    username_elem.send_keys(PLESK_USERNAME)
    password_elem.clear()
    password_elem.send_keys(PLESK_PASSWORD)
    submit_elem.click()

def add_new_certificate():
    driver.get(PLESK_URL + '/smb/ssl-certificate/add/id/{}'.format(SITE_ID))
    cert_name_elem = driver.find_element(By.ID, 'name')
    privkey_elem = driver.find_element(By.ID, 'privateKeyFile')
    cert_elem = driver.find_element(By.ID, 'certificateFile')
    upload_btn = driver.find_element(By.ID, 'btn-sendFiles')
    new_cert_name = CERT_PREFIX + str(int(time.time()))
    cert_name_elem.send_keys(new_cert_name)
    privkey_elem.send_keys(privkey_pem)
    cert_elem.send_keys(cert_pem)
    upload_btn.click()
    return new_cert_name

def load_certificate(new_cert_name):
    driver.get(PLESK_URL + '/smb/web/settings/id/{}'.format(SITE_ID))
    ssl_checkbox = driver.find_element(By.ID, 'sslSettings-ssl')
    ssl_certs = Select(driver.find_element(By.ID, 'sslSettings-certificateId'))
    send_button = driver.find_element(By.ID, 'btn-send')
    if not ssl_checkbox.is_selected():
        ssl_checkbox.click()
    found = False
    cert_id = None
    for cert_option in ssl_certs.options:
        if cert_option.text.find(new_cert_name) >= 0:
            found = True
            cert_id = cert_option.get_attribute('value')
            ssl_certs.select_by_value(cert_id)
            break
    if not found:
        raise Exception('failed to find newly loaded certificate')
    send_button.click()
    def cert_loaded(driver):
        elems = driver.find_elements(By.ID, 'btn-send')
        if len(elems) == 0:
            return True
        elif elems[0].get_attribute('disabled') is not None:
            return False
        else:
            raise Exception('loading certificate failed')
    WebDriverWait(driver, timeout=120).until(cert_loaded)
    return cert_id

def remove_old_certificates(new_cert_id):
    driver.get(PLESK_URL + '/smb/ssl-certificate/list/id/{}'.format(SITE_ID))
    remove_btn = driver.find_element(By.ID, 'buttonRemoveCertificate')
    any_to_remove = False
    for row in driver.find_elements(By.CSS_SELECTOR, 'tr[data-row-id]'):
        cert_id = row.get_attribute('data-row-id')
        if cert_id != new_cert_id:
            cert_link = driver.find_element(By.CSS_SELECTOR, 'a[href="/smb/ssl-certificate/edit/id/{}/certificateId/{}"]'.format(SITE_ID, cert_id))
            if cert_link.text.lower().startswith(CERT_PREFIX.lower()):
                cert_cbox = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][value="{}"]'.format(cert_id))
                cert_cbox.click()
                any_to_remove = True
    if any_to_remove:
        remove_btn.click()
        def confirm_exists(driver):
            return len(driver.find_elements(By.CSS_SELECTOR, '.confirmation-msg .btn-danger')) > 0
        WebDriverWait(driver, timeout=10).until(confirm_exists)
        driver.find_element(By.CSS_SELECTOR, '.confirmation-msg .btn-danger').click()
        def removed(driver):
            return len(driver.find_elements(By.CSS_SELECTOR, '.msg-content'))
        WebDriverWait(driver, timeout=10).until(removed)

print('Logging into Plesk...')
plesk_login()
print('Adding new certificate...')
new_cert_name = add_new_certificate()
print('Loading certificate...')
new_cert_id = load_certificate(new_cert_name)
print('Removing old certificate(s)...')
remove_old_certificates(new_cert_id)
print('Done!')