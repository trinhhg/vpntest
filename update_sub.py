import requests
import base64
import urllib.parse
import re
import datetime

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def clean_name_string(text):
    text = urllib.parse.unquote(text)
    if "剩余流量" in text: return text.replace("剩余流量：", "Data: ").replace("剩余流量:", "Data: ")
    if "距离下次重置剩余" in text: return text.replace("距离下次重置剩余：", "Reset: ").replace("距离下次重置剩余:", "Reset: ").replace(" 天", " Days")
    if "套餐到期" in text: return text.replace("套餐到期：", "Exp: ").replace("套餐到期:", "Exp: ")

    text = text.replace("良心云", "").replace("自动选择", "Auto Select").replace("故障转移", "Fallback")
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("🇸🇬新加坡", "🇸🇬 Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ").replace("🇺🇸美国", "🇺🇸 USA ").replace("🇰🇷韩国", "🇰🇷 Korea ")
    text = text.replace("台湾", "Taiwan ").replace("香港", "Hong Kong ").replace("新加坡", "Singapore ")
    text = text.replace("日本", "Japan ").replace("美国", "USA ").replace("韩国", "Korea ")
    text = text.replace("高速", " High Speed ").replace("专线", " Private ").replace("流媒体", " Streaming").replace("0.1倍", " 0.1x")
    
    text = re.sub(r'\|BGP\|', ' ', text)
    text = re.sub(r'\|BGP', ' ', text)
    text = re.sub(r'\|', ' ', text)
    
    clean_name = " ".join(text.split())
    return clean_name

def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        processed_tokens = set()
        
        for item in links_db:
            orig_url = item.get("orig")
            masked_url = item.get("masked")
            if not orig_url or not masked_url: continue
            
            parsed_url = urllib.parse.urlparse(masked_url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            
            # FIX: Bắt được cả link dùng OwO và token
            token_list = qs.get("OwO") or qs.get("token")
            if not token_list: continue
            token = token_list[0]
            
            if token in processed_tokens: continue
            processed_tokens.add(token)
                
            print(f"-> Đang xử lý Token: {token}")
            
            try:
                # CÚ LỪA 1: Giả vờ là v2rayN để xin file Base64
                b64_res = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23"}, timeout=15)
                # CÚ LỪA 2: Giả vờ là Clash để xin luôn file YAML chuẩn
                yaml_res = requests.get(orig_url, headers={"User-Agent": "Clash-Verge"}, timeout=15)
                
                if b64_res.status_code != 200: continue
                
                # --- 1. XỬ LÝ DUNG LƯỢNG VÀ BASE64 ---
                content = b64_res.text.strip()
                user_info = b64_res.headers.get("subscription-userinfo", "")
                
                traffic_data = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Không giới hạn"}
                if user_info:
                    match_up = re.search(r'upload=(\d+)', user_info)
                    match_down = re.search(r'download=(\d+)', user_info)
                    match_total = re.search(r'total=(\d+)', user_info)
                    match_exp = re.search(r'expire=(\d+)', user_info)
                    
                    up = int(match_up.group(1)) if match_up else 0
                    down = int(match_down.group(1)) if match_down else 0
                    total = int(match_total.group(1)) if match_total else 0
                    exp = int(match_exp.group(1)) if match_exp else 0
                    
                    used_gb = (up + down) / 1073741824
                    total_gb = total / 1073741824
                    percent = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                    exp_str = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                        
                    traffic_data = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": percent, "expire": exp_str}

                missing_padding = len(content) % 4
                if missing_padding: content += '=' * (4 - missing_padding)
                
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                lines = decoded.splitlines()
                new_lines = []
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if "://" in line:
                        try:
                            parts = line.split("#", 1)
                            if len(parts) == 2:
                                new_name = clean_name_string(parts[1])
                                new_lines.append(f"{parts[0]}#{new_name} | VPN Trinh Hg")
                            else: new_lines.append(line)
                        except: new_lines.append(line)
                    else: new_lines.append(line)

                final_string = "\n".join(new_lines) if new_lines else decoded
                final_b64 = base64.b64encode(final_string.encode()).decode()
                missing = len(final_b64) % 4
                if missing: final_b64 += "=" * (4 - missing)
                
                # --- 2. XỬ LÝ YAML ---
                yaml_text = yaml_res.text
                if "proxies:" in yaml_text:
                    # Chạy hàm dọn dẹp tên quốc gia, BGP...
                    yaml_text = clean_name_string(yaml_text)
                    # Dùng Regex để tự động nhét " | VPN Trinh Hg" vào cuối tên node trong file YAML
                    yaml_text = re.sub(r'^( +- name:\s*[\'"]?)(.*?)([\'"]?)$', r'\1\2 | VPN Trinh Hg\3', yaml_text, flags=re.MULTILINE)
                else:
                    yaml_text = ""

                # PUSH CẢ 2 BẢN LÊN DATABASE
                payload = {
                    "key": token,
                    "body_b64": final_b64,
                    "body_yaml": yaml_text,
                    "info": user_info,
                    "traffic": traffic_data
                }
                push_res = requests.post(API_PUSH, json=payload, timeout=10)
                print(f"  [OK] Đã push thành công: {token}" if push_res.status_code == 200 else f"  [FAIL] Push lỗi")
            except Exception as e:
                print(f"  [!] Lỗi xử lý Node: {e}")
    except Exception as e: print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    update_all_subs()
