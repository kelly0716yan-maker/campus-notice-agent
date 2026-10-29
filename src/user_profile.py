"""用户画像（记忆）：保存在本地 data/profile.json，用来判断“这条通知和我有没有关系”。
该文件含个人信息，已加入 .gitignore，不会上传到 GitHub。"""
import json
from pathlib import Path

PROFILE_PATH = Path("data/profile.json")
ROLE_OPTIONS = ["学生干部", "中共党员（含预备党员）", "入团积极分子", "班委", "有保研意向", "有就业意向", "有考研意向", "有出国意向"]
DEFAULT = {"grade": "", "major": "", "roles": [], "interests": ""}


def load_profile(path=PROFILE_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        return dict(DEFAULT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT)
    return {**DEFAULT, **{k: data.get(k, v) for k, v in DEFAULT.items()}}


def save_profile(profile: dict, path=PROFILE_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: profile.get(k, v) for k, v in DEFAULT.items()}
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def is_filled(profile: dict) -> bool:
    return bool(profile.get("grade") or profile.get("major") or profile.get("roles") or profile.get("interests"))


def profile_text(profile: dict) -> str:
    roles = "、".join(profile.get("roles", [])) or "未填"
    return (f"年级：{profile.get('grade') or '未填'}；学院/专业：{profile.get('major') or '未填'}；"
            f"身份：{roles}；关注：{profile.get('interests') or '未填'}")
