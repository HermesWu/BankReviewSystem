# myapp_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re

def get_myapp_data(pkg_name="com.ecitic.bank.mobile", days_limit=14):
    print(f"🚀 启动应用宝采集 (严格日期过滤版, 近 {days_limit} 天)...")
    raw_reviews = []
    now = pd.Timestamp.now().tz_localize(None)
    threshold_date = now - pd.Timedelta(days=days_limit)
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        page = browser.new_page()
        
        try:
            url = f"https://sj.qq.com/appdetail/{pkg_name}"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000)
            
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    if re.search(r'comment|review|reply', class_name, re.IGNORECASE):
                        text = div.inner_text().replace('\n', ' | ')
                        if len(text) < 15: continue
                        
                        date_match = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text)
                        short_date_match = re.search(r'(?<!\d)(\d{1,2})[-/月](\d{1,2})[日]?(?!\d)', text)
                        
                        review_date = None
                        
                        try:
                            if date_match:
                                y, m, d = date_match.groups()
                                review_date = pd.to_datetime(f"{y}-{m}-{d}")
                            elif "刚刚" in text or "分钟前" in text or "小时前" in text or "今天" in text:
                                review_date = now
                            elif "昨天" in text:
                                review_date = now - pd.Timedelta(days=1)
                            elif "前天" in text:
                                review_date = now - pd.Timedelta(days=2)
                            elif short_date_match:
                                m, d = short_date_match.groups()
                                current_year = now.year
                                review_date = pd.to_datetime(f"{current_year}-{m}-{d}")
                                
                                # 🚨 核心修复：如果拼出来的日期大于今天（在未来），说明它是去年的评论！
                                if review_date > now:
                                    review_date = pd.to_datetime(f"{current_year - 1}-{m}-{d}")
                        except Exception:
                            continue # 如果拼出不存在的日期（如 2月30日）直接忽略
                        
                        if review_date:
                            if review_date < threshold_date: 
                                continue # 真正的时间过滤，超过天数就抛弃
                                
                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "腾讯应用宝",
                                "日期": date_str,
                                "具体时间": date_str + " 00:00:00",
                                "标题": "无标题",
                                "内容": text,
                                "评分": 0
                            })
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"❌ 应用宝抓取异常: {e}")
        finally:
            browser.close()
            
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]