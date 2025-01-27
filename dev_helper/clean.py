import argparse
from argparse import Namespace
from pathlib import Path
import shutil


def clean_directory(directory: Path):
    """清理指定目录内的所有文件和子目录"""
    if not directory.exists():
        print(f"目录 {directory} 不存在，跳过清理。")
        return

    for item in directory.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()  # 删除文件或符号链接
                print(f"已删除文件: {item}")
            elif item.is_dir():
                shutil.rmtree(item)  # 删除目录
                print(f"已删除目录: {item}")
        except Exception as e:
            print(f"清理 {item} 时出错: {e}")


def main():
    parser = argparse.ArgumentParser(description="清理指定的文件夹内容。")
    parser.add_argument(
        "--file",
        choices=["logs", "comments", "anchor"],
        required=True,
        help="指定要清理的文件夹: logs, comments, anchor",
    )
    args: Namespace = parser.parse_args()

    # 根据 --file 参数选择清理目录
    current_file = Path(__file__).resolve()  # 获取当前脚本的绝对路径
    base_path = current_file.parent.parent  # 获取项目的父级目录

    directories = {
        "logs": base_path / "logs",
        "comments": base_path / "comments",
        "anchor": base_path / "anchor",
    }

    selected_dir = directories.get(args.file)
    if selected_dir:
        print(f"正在清理目录: {selected_dir}")
        clean_directory(selected_dir)


if __name__ == "__main__":
    main()
