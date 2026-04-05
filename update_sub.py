import requests
import base64
import urllib.parse
import re

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def process_node_name(text):
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
    return f"{clean_name} | VPN Trinh Hg"

def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        
        for item in links_db:
            orig_url = item.get("orig")
            if not orig_url: continue
                
            parsed_url = urllib.parse.urlparse(orig_url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            token = qs.get("OwO", [None])[0]
            
            if not token: 
                continue
                
            print(f"-> Đang xử lý Token: {token}")
            headers = {"User-Agent": "v2rayN/6.23"}
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content: continue
                    
                    user_info = sub_res.headers.get("subscription-userinfo", "")
                    missing_padding = len(content) % 4
                    if missing_padding: content += '=' * (4 - missing_padding)
                    
                    try:
                        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                        lines = decoded.splitlines()
                        new_lines = []
                        
                        for line in lines:
                            # FIX LỖI TRIM() NGỚ NGẨN BẰNG STRIP()
                            line = line.strip()
                            if not line: continue
                            if "://" in line:
                                try:
                                    parts = line.split("#", 1)
                                    if len(parts) == 2:
                                        new_name = process_node_name(parts[1])
                                        new_lines.append(f"{parts[0]}#{urllib.parse.quote(new_name)}")
                                    else:
                                        new_lines.append(line)
                                except: new_lines.append(line)
                            else:
                                new_lines.append(line)

                        if not new_lines: final_string = decoded
                        else: final_string = "\n".join(new_lines)
                        
                        final_b64 = base64.b64encode(final_string.encode('utf-8')).decode('utf-8').replace('\n', '')
                        
                        payload = {"key": token, "body": final_b64, "info": user_info}
                        requests.post(API_PUSH, json=payload, timeout=10)
                        print(f"  [OK] Đã push thành công data cho Token {token}")
                            
                    except Exception as e: print(f"  [!] Lỗi Base64: {e}")
            except Exception as e: print(f"  [!] Lỗi lấy sub: {e}")
    except Exception as e: print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    update_all_subs()
