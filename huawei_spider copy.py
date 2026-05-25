# huawei_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re

def get_huawei_data(app_id="C10350054", days_limit=14):
    print(f"🚀 启动华为渠道采集 (严格日期过滤版, 近 {days_limit} 天)...")
    raw_reviews = []
    threshold_date = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=days_limit)
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        page = browser.new_page()
        
        try:
            url = f"https://appgallery.huawei.com/app/{app_id}"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000) 
            
            for _ in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    if re.search(r'comment|review', class_name, re.IGNORECASE):
                        text = div.inner_text().replace('\n', ' | ')
                        if len(text) < 15: continue
                        
                        # 华为的评价通常带有完整的年月日
                        date_match = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text)
                        
                        if date_match:
                            y, m, d = date_match.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                            
                            if review_date < threshold_date: 
                                continue # 超过设定天数，丢弃
                                
                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "华为市场",
                                "日期": date_str,
                                "具体时间": date_str + " 00:00:00",
                                "标题": "无标题",
                                "内容": text,
                                "评分": 0
                            })
                        else:
                            # 🚨 找不到日期特征，抛弃！
                            continue
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"❌ 华为抓取异常: {e}")
        finally:
            browser.close() 
            
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]