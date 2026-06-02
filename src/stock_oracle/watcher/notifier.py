"""桌面通知（plyer 优先，失败时降级为控制台打印）。"""
import sys
from typing import Optional


def notify(title: str, message: str, timeout: int = 10) -> bool:
    """发出桌面通知。返回 True 表示通知成功。"""
    try:
        from plyer import notification  # type: ignore
        notification.notify(title=title, message=message, timeout=timeout)
        return True
    except Exception:
        # 降级：打印到控制台
        print(f"[通知] {title} — {message}", file=sys.stderr)
        return False


def play_sound(sound_file: Optional[str] = None) -> bool:
    """播放提示音（可选）。"""
    try:
        if sound_file:
            if sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["afplay", sound_file])
                return True
            elif sys.platform.startswith("win"):
                import winsound  # type: ignore
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
        # 默认提示音
        if sys.platform.startswith("win"):
            import winsound  # type: ignore
            winsound.Beep(1000, 200)
            return True
        print("\a", end="", flush=True)
        return True
    except Exception:
        return False
