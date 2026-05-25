from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from main import run_agent_task
import uvicorn
import os
import datetime

app = FastAPI()

# ======= 1. 抓取与分析接口 =======
@app.get("/analyze")
def analyze_reviews(request: Request, days: int = 7):
    print(f"🤖 收到机器人请求！要求抓取近 {days} 天的数据...")
    
    # 1. 调用爬虫和 AI
    result = run_agent_task(query_days=days)
    
    # ======= 🪄 新增：生成带时间戳的新文件名 =======
    # 获取当前时间，格式如：20260513_113045
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 构建新文件名，加上查询的天数，更清晰
    new_report_name = f"report_{days}days_{timestamp}.html"
    
    # 将刚生成的通用报告，重命名为我们带时间戳的新名字
    original_file = "全渠道评价分析报告.html"
    if os.path.exists(original_file):
        os.rename(original_file, new_report_name)
    # ================================================

    # ======= 🪄 英文马甲转换代码 (保持之前的修改不变) =======
    if "data" in result and isinstance(result["data"], list):
        english_data = []
        for item in result["data"]:
            english_data.append({
                "source": item.get("来源", ""),
                "score": item.get("评分", 0),
                "sentiment": item.get("情感倾向", ""),
                "category": item.get("问题分类", ""),
                "summary": item.get("一句话总结", "")
            })
        result["data"] = english_data
    # =======================================================
    
    # 2. 动态捕获当前链接，并拼接上刚刚生成的新文件名
    host = request.headers.get('host', '127.0.0.1:8000')
    scheme = "https" if "ngrok" in host else "http"
    
    # 💡 核心修改：链接后面跟的是新文件名，而不是固定的 /report
    report_link = f"{scheme}://{host}/report/{new_report_name}"
    
    result["report_link"] = report_link
    
    if result.get("status") == "success":
        result["message"] += " \n\n可视化大屏已更新，可通过下方链接查看。"
    elif result.get("status") == "empty":
        result["message"] += " \n\n（虽然没有新数据，但您仍可点击下方链接查看存量的历史报告）"
        
    return result

# ======= 2. 新增：在线展示 HTML 报告接口 =======
# 💡 核心修改：使用路径参数 {filename} 来接收不同的报告名字
@app.get("/report/{filename}")
def serve_html_report(filename: str):
    # 让它去 reports 文件夹里面找！
    REPORT_DIR = "reports"
    file_path = os.path.join(REPORT_DIR, filename)
    
    # 🌟 修改点 1：放宽安全检查，允许 "分析报告_" 或 "report_" 开头
    if not (filename.startswith("report_") or filename.startswith("分析报告_")) or not filename.endswith(".html"):
        return {"error": "非法的文件请求！"}
        
    if os.path.exists(file_path):
        # 🌟 修改点 2：这里必须传 file_path (带路径的)，不能传 filename！
        return FileResponse(file_path, media_type="text/html")
    else:
        return {"error": "抱歉，该报告文件不存在或已被删除！"}

if __name__ == "__main__":
    print("🌟 智能体后台 API 已启动！正在监听机器人的呼唤...")
    uvicorn.run(app, host="0.0.0.0", port=8000)