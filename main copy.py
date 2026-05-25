# main.py
import pandas as pd
import json
import time
from openai import OpenAI
from datetime import datetime

# ======= 1. 导入采集模块 =======
from apple_fetcher import get_apple_data
from huawei_spider import get_huawei_data
from myapp_spider import get_myapp_data

# ======= 2. 核心配置区 =======
YOUR_API_KEY = "sk-cd07e5b69144417186adf31b2f94f426"
QUERY_DAYS = 14  
TOP_N = 5  

client = OpenAI(api_key=YOUR_API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

APPLE_ID = "422844108"   
HUAWEI_ID = "C10350054" 
MYAPP_PKG = "com.ecitic.bank.mobile"     

def generate_report(results, top_n=5):
    """生成 HTML 可视化报告的函数"""
    df_final = pd.DataFrame(results)
    
    for col in ['日期', '评分', '情感倾向', '来源', '内容', '问题分类', '一句话总结']:
        if col not in df_final.columns:
            df_final[col] = "暂无"

    df_final = df_final.sort_values(by=['日期', '评分'], ascending=[False, True])
    
    total_reviews = len(df_final)
    sentiment_counts = df_final['情感倾向'].value_counts().to_dict()
    pos_count = sentiment_counts.get('正向', 0)
    neu_count = sentiment_counts.get('中性', 0)
    neg_count = sentiment_counts.get('负向', 0)

    pos_pct = f"{(pos_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"
    neu_pct = f"{(neu_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"
    neg_pct = f"{(neg_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"

    sources = df_final['来源'].value_counts().to_dict()
    apple_c = sources.get("App Store", 0) + sources.get("Apple Store", 0)
    huawei_c = sources.get("华为市场", 0) + sources.get("华为应用市场", 0)
    myapp_c = sources.get("腾讯应用宝", 0)

    if total_reviews > 0:
        daily_df = df_final.groupby(['日期', '来源']).size().unstack(fill_value=0).reset_index()
        daily_df.columns.name = None 
        
        for col in ['华为市场', '腾讯应用宝', 'App Store', 'Apple Store']:
            if col not in daily_df.columns:
                daily_df[col] = 0
        
        daily_df['苹果App Store'] = daily_df['App Store'] + daily_df['Apple Store']
        daily_df = daily_df[['日期', '华为市场', '腾讯应用宝', '苹果App Store']]
        daily_df['合计'] = daily_df['华为市场'] + daily_df['腾讯应用宝'] + daily_df['苹果App Store']
        daily_df = daily_df.sort_values(by='日期', ascending=False)
        
        for col in ['华为市场', '腾讯应用宝', '苹果App Store', '合计']:
            daily_df[col] = daily_df[col].astype(str) + " 条"
            
        daily_table_html = daily_df.to_html(index=False, classes="data-table daily-table", escape=False)
    else:
        daily_table_html = "<p>暂无每日数据统计</p>"

    neg_df = df_final[df_final['情感倾向'] == '负向']
    neg_issues_list = "<li>暂无</li>"
    bad_cards = ""
    if not neg_df.empty:
        neg_top = neg_df['问题分类'].value_counts().head(top_n)
        neg_issues_list = "".join([f"<li>🔴 <b>{k}</b>：{v}次</li>" for k, v in neg_top.items()])
        for _, row in neg_df.sort_values(by='评分').head(top_n).iterrows():
            bad_cards += f'<div class="review-mini-card bad-card"><div class="rmc-header"><span class="rmc-tag bad-tag">【{row["问题分类"]}】</span><span>{row["评分"]}星</span></div><div class="rmc-content">"{row["内容"][:150]}..."</div><div class="rmc-ai">🤖 AI总结：{row["一句话总结"]}</div></div>'

    pos_df = df_final[df_final['情感倾向'] == '正向']
    pos_issues_list = "<li>暂无</li>"
    good_cards = ""
    if not pos_df.empty:
        pos_top = pos_df['问题分类'].value_counts().head(top_n)
        pos_issues_list = "".join([f"<li>🟢 <b>{k}</b>：{v}次</li>" for k, v in pos_top.items()])
        for _, row in pos_df.sort_values(by='评分', ascending=False).head(top_n).iterrows():
            good_cards += f'<div class="review-mini-card good-card"><div class="rmc-header"><span class="rmc-tag good-tag">【{row["问题分类"]}】</span><span>{row["评分"]}星</span></div><div class="rmc-content">"{row["内容"][:150]}..."</div><div class="rmc-ai">🤖 AI总结：{row["一句话总结"]}</div></div>'

    display_columns = ['来源', '具体时间', '标题', '内容', '评分', '情感倾向', '问题分类', '一句话总结']
    actual_display_columns = [col for col in display_columns if col in df_final.columns]
    detail_display_df = df_final[actual_display_columns]
    table_html = detail_display_df.to_html(index=False, classes="data-table", escape=False)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>全渠道评价分析报告</title>
        <style>
            body {{ font-family: sans-serif; background: #f5f7fa; padding: 20px; color:#333; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .dashboard {{ display: flex; gap: 15px; margin-bottom: 30px; }}
            .card {{ flex: 1; padding: 20px; border-radius: 8px; text-align: center; color: white; }}
            .card-total {{ background: #34495e; }} .card-pos {{ background: #27ae60; }} .card-neg {{ background: #e74c3c; }} .card-neu {{ background: #f39c12; }}
            .card h2 {{ margin: 10px 0 0; font-size: 32px; }}
            .pct {{ font-size: 16px; opacity: 0.85; margin-left: 5px; font-weight: normal; }}
            .insights {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .insight-box {{ flex: 1; border: 1px solid #eee; padding: 20px; border-radius: 8px; border-top: 4px solid #ccc; background:#fcfcfc; }}
            .box-title {{ margin-top: 0; color: #2c3e50; border-bottom: 1px dashed #ddd; padding-bottom: 10px; margin-bottom: 15px; }}
            .review-mini-card {{ background: #f9f9f9; padding: 10px; margin-top: 10px; border-radius: 4px; font-size: 13px; }}
            .bad-card {{ border-left: 4px solid #e74c3c; }} .good-card {{ border-left: 4px solid #27ae60; }}
            .rmc-header {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-weight: bold; }}
            .rmc-ai {{ background: #e8f4f8; display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 12px; font-weight:bold; color: #333; }}
            .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }}
            .data-table th, .data-table td {{ border: 1px solid #eee; padding: 10px; text-align: left; }}
            .data-table th {{ background: #f8f9fa; }}
            .daily-table th {{ background: #e8f4f8; text-align: center; }}
            .daily-table td {{ text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align:center; padding-bottom:15px; border-bottom: 2px solid #eee;">📊 APP 全渠道评价智能分析报告</h1>
            
            <div class="dashboard">
                <div class="card card-total"><h3>总数</h3><h2>{total_reviews}</h2></div>
                <div class="card card-pos"><h3>好评</h3><h2>{pos_count}<span class="pct">({pos_pct})</span></h2></div>
                <div class="card card-neu"><h3>中评</h3><h2>{neu_count}<span class="pct">({neu_pct})</span></h2></div>
                <div class="card card-neg"><h3>差评</h3><h2>{neg_count}<span class="pct">({neg_pct})</span></h2></div>
            </div>

            <div class="insights">
                <div class="insight-box" style="flex: 1; border-top-color: #3498db;">
                    <h3 class="box-title">📊 总体渠道概况</h3>
                    <p style="font-weight: bold;">总评论数：{total_reviews} 条</p>
                    <ul style="list-style: none; padding: 0; line-height: 2.0;">
                        <li>🔹 华为应用市场：<b>{huawei_c}</b> 条</li>
                        <li>🔹 腾讯应用宝：<b>{myapp_c}</b> 条</li>
                        <li>🔹 苹果App Store：<b>{apple_c}</b> 条</li>
                    </ul>
                </div>
                <div class="insight-box" style="flex: 2; border-top-color: #9b59b6;">
                    <h3 class="box-title">📈 每日市场评论数量统计</h3>
                    <div style="overflow-x: auto;">{daily_table_html}</div>
                </div>
            </div>

            <div class="insights">
                <div class="insight-box" style="border-top-color: #e74c3c;">
                    <h3>📉 差评雷区 TOP {top_n}</h3><ul>{neg_issues_list}</ul>{bad_cards}
                </div>
                <div class="insight-box" style="border-top-color: #27ae60;">
                    <h3>📈 好评亮点 TOP {top_n}</h3><ul>{pos_issues_list}</ul>{good_cards}
                </div>
            </div>
            
            <h3 style="margin-top:20px; padding-bottom: 10px; border-bottom: 2px solid #eee;">🔍 评价明细清单</h3>
            <div style="overflow-x: auto;">{table_html}</div>
        </div>
    </body>
    </html>
    """
    with open("全渠道评价分析报告.html", "w", encoding="utf-8") as f:
        f.write(html_content)

# 💡 核心修改区：将原先的 main() 改名为 run_agent_task，并支持传入天数，返回 JSON 给机器人
def run_agent_task(query_days=7):
    print(f"\n🚀 API任务启动：正在全网搜寻近 {query_days} 天的三端最新评价...")
    all_data = []
    
    try: all_data.extend(get_apple_data(APPLE_ID, days_limit=query_days))
    except: pass
    try: all_data.extend(get_huawei_data(HUAWEI_ID, days_limit=query_days))
    except: pass
    try: all_data.extend(get_myapp_data(MYAPP_PKG, days_limit=query_days))
    except: pass

    if not all_data:
        # 直接返回空状态的 JSON 字典给 FastAPI
        return {"status": "empty", "message": f"最近 {query_days} 天内，三端均未产生新评价。"}

    final_results = []
    for index, item in enumerate(all_data):
        print(f"🧠 AI 分析中 ({index+1}/{len(all_data)}) - 来源: {item['来源']}...")
        prompt = f"""
        你是一个银行产品经理。请分析这条来自{item['来源']}的用户评价：
        "{item['内容']}"
        提取真实评论正文，严格按 JSON 输出：
        {{
            "情感倾向": "正向/中性/负向",
            "问题分类": "闪退/UI/功能/服务/其他",
            "一句话总结": "十个字概括核心诉求"
        }}
        """
        try:
            res = client.chat.completions.create(model="qwen-plus", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
            item.update(json.loads(res.choices[0].message.content))
            final_results.append(item)
        except: continue
        time.sleep(0.5)

    generate_report(final_results, top_n=TOP_N)
    
    # 💡 核心：任务完成后，将总结打包成 JSON 格式返回，这就是给智能体吃的“数据饲料”
    total = len(final_results)
    bad_count = len([x for x in final_results if x.get('情感倾向') == '负向'])
    summary = f"报告已生成！共抓取 {total} 条有效评价，其中发现 {bad_count} 条差评。详细排版报告已保存在本地服务器。"
    
    print(f"🎉 {summary}")
    return {"status": "success", "message": summary, "data": final_results}

if __name__ == "__main__":
    # 如果你在终端里直接跑 python3 main.py，它依然能按默认配置正常运行
    run_agent_task(query_days=QUERY_DAYS)