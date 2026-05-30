"""
交互节点控制器 - 在关键节点暂停并询问用户确认
"""
from typing import Dict, List

class InteractiveController:
    """交互节点控制器"""
    
    def __init__(self):
        self.confirmed = {}
    
    def ask_basic_info(self) -> Dict[str, str]:
        """节点1：询问基本信息"""
        print("\n=== 📊 ShuoC Ppt - 开始制作 ===\n")
        info = {}
        info["title"]    = input("📌 PPT主题/标题：").strip()
        info["author"]   = input("👤 汇报人姓名：").strip()
        info["advisor"]  = input("👨‍🏫 导师/指导（可选，直接回车跳过）：").strip()
        info["date"]     = input("📅 日期（可选，直接回车跳过）：").strip()
        scene_map = {"1":"学术汇报","2":"商业报告","3":"推免答辩","4":"科研总结","5":"通用"}
        print("\n🎨 场景类型：1.学术汇报  2.商业报告  3.推免答辩  4.科研总结  5.通用")
        s = input("选择场景（默认5）：").strip() or "5"
        info["scene"] = scene_map.get(s, "通用")
        style_map = {"1":"专业蓝","2":"学术深蓝","3":"简约灰","4":"商务黑"}
        print("\n🎨 配色风格：1.专业蓝  2.学术深蓝  3.简约灰  4.商务黑")
        st = input("选择风格（默认1）：").strip() or "1"
        info["style"] = style_map.get(st, "专业蓝")
        return info
    
    def confirm_outline(self, outline: List[Dict]) -> bool:
        """节点2：确认大纲"""
        print("\n=== 📋 大纲预览（请确认）===\n")
        for i, section in enumerate(outline, 1):
            title = section.get("title","")
            stype = section.get("type","list")
            count = len(section.get("items", section.get("points", section.get("events",[]))))
            print(f"  {i}. {title}（{stype}，{count}条内容）")
        print()
        ans = input("确认大纲？[Y/n/修改]：").strip().lower()
        if ans in ("n","no","否"):
            return False
        if ans in ("修改","edit","e"):
            print("请重新输入修改意见（输入完成后按 Enter）：")
            feedback = input().strip()
            self.confirmed["outline_feedback"] = feedback
            return False
        return True
    
    def confirm_generate(self, page_count: int) -> bool:
        """节点3：确认生成"""
        print(f"\n=== ✅ 准备生成 {page_count} 页 PPT ===")
        ans = input("确认生成？[Y/n]：").strip().lower()
        return ans not in ("n","no","否")
    
    def ask_output_path(self) -> str:
        """询问输出路径"""
        path = input("\n💾 输出文件名（默认 output.pptx）：").strip()
        return path or "output.pptx"
    
    def ask_modification(self) -> str:
        """节点4：生成后询问修改"""
        print("\n=== 🔧 PPT已生成 ===")
        ans = input("是否需要修改？[y/N]：").strip().lower()
        if ans in ("y","yes","是"):
            return input("请描述修改内容：").strip()
        return ""
