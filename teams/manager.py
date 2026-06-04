"""
团队管理模块 - Team Manager
支持企业猎头场景下的团队协作
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class TeamRole(str, Enum):
    """团队角色"""
    ADMIN = "admin"           # 管理员：完全控制
    MANAGER = "manager"       # 经理：管理职位和成员
    RECRUITER = "recruiter"   # 招聘者：搜索和追踪候选人
    VIEWER = "viewer"         # 查看者：只读权限


class TeamManager:
    """团队管理器"""

    def __init__(self, data_dir: str = "~/.jobtracer/teams"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.teams_file = self.data_dir / "teams.json"
        self._teams = self._load_teams()

    def _load_teams(self) -> dict:
        """加载团队数据"""
        if self.teams_file.exists():
            with open(self.teams_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"teams": [], "members": {}, "invitations": {}}

    def _save_teams(self):
        """保存团队数据"""
        with open(self.teams_file, "w", encoding="utf-8") as f:
            json.dump(self._teams, f, ensure_ascii=False, indent=2)

    def create_team(self, name: str, owner_id: str, description: str = "") -> dict:
        """
        创建团队
        
        Args:
            name: 团队名称
            owner_id: 所有者ID
            description: 团队描述
        
        Returns:
            团队信息字典
        """
        team_id = str(uuid.uuid4())[:8]
        team = {
            "team_id": team_id,
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "members": [owner_id],
            "stats": {
                "total_positions": 0,
                "total_candidates": 0,
                "interviews_scheduled": 0,
                "offers_extended": 0,
                "deals_closed": 0
            }
        }
        self._teams["teams"].append(team)
        
        # 设置所有者为管理员
        self._teams["members"][owner_id] = {
            "user_id": owner_id,
            "role": TeamRole.ADMIN.value,
            "joined_at": datetime.now().isoformat()
        }
        
        self._save_teams()
        return team

    def invite_member(self, team_id: str, email: str, role: str = TeamRole.RECRUITER.value) -> dict:
        """
        邀请成员加入团队
        
        Args:
            team_id: 团队ID
            email: 成员邮箱
            role: 角色
        
        Returns:
            邀请信息
        """
        # 查找团队
        team = next((t for t in self._teams["teams"] if t["team_id"] == team_id), None)
        if not team:
            return {"success": False, "error": "团队不存在"}
        
        # 生成邀请
        invite_id = str(uuid.uuid4())[:8]
        invitation = {
            "invite_id": invite_id,
            "team_id": team_id,
            "email": email,
            "role": role,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": datetime.now().isoformat()  # 7天有效期可扩展
        }
        
        if invite_id not in self._teams["invitations"]:
            self._teams["invitations"][invite_id] = {}
        self._teams["invitations"][invite_id] = invitation
        self._save_teams()
        
        return {"success": True, "invite_id": invite_id, "invitation": invitation}

    def accept_invitation(self, invite_id: str, user_id: str) -> dict:
        """
        接受邀请
        
        Args:
            invite_id: 邀请ID
            user_id: 用户ID
        
        Returns:
            结果
        """
        invitation = self._teams["invitations"].get(invite_id)
        if not invitation or invitation.get("status") != "pending":
            return {"success": False, "error": "邀请无效或已过期"}
        
        team = next((t for t in self._teams["teams"] if t["team_id"] == invitation["team_id"]), None)
        if not team:
            return {"success": False, "error": "团队不存在"}
        
        # 添加成员
        if user_id not in team["members"]:
            team["members"].append(user_id)
        
        self._teams["members"][user_id] = {
            "user_id": user_id,
            "role": invitation["role"],
            "joined_at": datetime.now().isoformat()
        }
        
        invitation["status"] = "accepted"
        invitation["accepted_at"] = datetime.now().isoformat()
        
        self._save_teams()
        return {"success": True, "team_id": team["team_id"], "role": invitation["role"]}

    def remove_member(self, team_id: str, member_id: str, operator_id: str) -> dict:
        """移除成员"""
        team = next((t for t in self._teams["teams"] if t["team_id"] == team_id), None)
        if not team:
            return {"success": False, "error": "团队不存在"}
        
        # 检查操作权限
        if operator_id != team["owner_id"]:
            operator_role = self._teams["members"].get(operator_id, {}).get("role")
            if operator_role != TeamRole.ADMIN.value:
                return {"success": False, "error": "权限不足"}
        
        if member_id in team["members"]:
            team["members"].remove(member_id)
        
        self._save_teams()
        return {"success": True}

    def get_team(self, team_id: str) -> Optional[dict]:
        """获取团队信息"""
        return next((t for t in self._teams["teams"] if t["team_id"] == team_id), None)

    def get_member_role(self, team_id: str, user_id: str) -> Optional[str]:
        """获取成员角色"""
        team = self.get_team(team_id)
        if not team:
            return None
        member_info = self._teams["members"].get(user_id, {})
        return member_info.get("role")

    def update_team_stats(self, team_id: str, stats: dict) -> dict:
        """更新团队统计"""
        team = self.get_team(team_id)
        if not team:
            return {"success": False, "error": "团队不存在"}
        
        team["stats"].update(stats)
        team["updated_at"] = datetime.now().isoformat()
        self._save_teams()
        return {"success": True, "stats": team["stats"]}

    def get_team_dashboard(self, team_id: str) -> dict:
        """
        获取团队数据看板
        
        Args:
            team_id: 团队ID
        
        Returns:
            看板数据字典
        """
        team = self.get_team(team_id)
        if not team:
            return {"success": False, "error": "团队不存在"}
        
        # 获取所有成员信息
        members_info = []
        for member_id in team["members"]:
            member_data = self._teams["members"].get(member_id, {})
            members_info.append({
                "user_id": member_id,
                "role": member_data.get("role", TeamRole.VIEWER.value),
                "joined_at": member_data.get("joined_at", "")
            })
        
        return {
            "team_id": team_id,
            "name": team["name"],
            "description": team["description"],
            "created_at": team["created_at"],
            "owner_id": team["owner_id"],
            "members": members_info,
            "stats": team["stats"],
            "recent_activity": self._get_recent_activity(team_id)
        }

    def _get_recent_activity(self, team_id: str) -> list:
        """获取最近活动"""
        # 可扩展为从外部数据源获取真实活动
        return [
            {"type": "position_added", "timestamp": datetime.now().isoformat(), "description": "新增职位"},
            {"type": "candidate_added", "timestamp": datetime.now().isoformat(), "description": "添加候选人"}
        ]

    def list_teams(self, user_id: str = None) -> list:
        """列出团队"""
        teams = self._teams["teams"]
        if user_id:
            teams = [t for t in teams if user_id in t["members"]]
        return teams


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    manager = TeamManager()
    
    # 创建团队
    team = manager.create_team(
        name="Tech猎头团队",
        owner_id="user_001",
        description="专注互联网技术岗位招聘"
    )
    print(f"✅ 团队创建成功: {team['team_id']} - {team['name']}")
    
    # 邀请成员
    invite = manager.invite_member(team["team_id"], "recruiter@example.com", TeamRole.RECRUITER.value)
    print(f"✅ 邀请发送: {invite['invite_id']}")
    
    # 获取看板
    dashboard = manager.get_team_dashboard(team["team_id"])
    print(f"\n📊 团队看板:")
    print(f"  团队名: {dashboard['name']}")
    print(f"  成员数: {len(dashboard['members'])}")
    print(f"  统计: {dashboard['stats']}")