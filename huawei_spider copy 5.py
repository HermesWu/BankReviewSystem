# huawei_spider.py
from playwright.sync_api import sync_playwright
import re

def get_huawei_data(app_id="C10350054", days_limit=14):
    print("🚀 启动华为渠道采集 (HTML X光侦探模式)...")
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        page = browser.new_page()
        
        try:
            url = f"https://appgallery.huawei.com/app/{app_id}"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000) 
            
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    
                    if re.search(r'comment|review', class_name, re.IGNORECASE) and \
                       not re.search(r'list|container|wrapper|section|group|box', class_name, re.IGNORECASE):
                       
                        text = div.inner_text()
                        if not text or len(text) < 15: continue
                        
                        text_clean = text.replace('\n', ' | ')
                        if "查看全部" in text_clean and "人评分" in text_clean: continue
                        if len(re.findall(r'202\d[-/\.年]\d{1,2}[-/\.月]\d{1,2}', text_clean)) > 2: continue
                        
                        # 🎯 核心：抓到第一条真实评价，直接打印它的底层 HTML 源码！
                        print("\n" + "="*60)
                        print("🕵️‍♂️ 发现目标！请将下面这坨 HTML 代码复制发给 Gemini：\n")
                        print(div.inner_html())
                        print("="*60 + "\n")
                        
                        # 打印完一条就直接强制结束，不往下跑了
                        return []
                        
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"❌ 抓取异常: {e}")
        finally:
            browser.close() 
            
    return []