import asyncio
from pathlib import Path

from watchfiles import awatch

from codn.utils.pyright_lsp_client import PyrightLSPClient, path_to_file_uri


async def watch_and_sync(client, project_path):
    async for changes in awatch(project_path):
        for change_type, changed_path in changes:
            uri = path_to_file_uri(changed_path)
            if change_type.name in ("added", "modified"):
                with open(changed_path, encoding="utf-8") as f:
                    content = f.read()
                # 这里假设客户端有 send_did_open 和 send_did_change 方法
                await client.send_did_open(uri, content)
            elif change_type.name == "deleted":
                # 发送关闭通知
                await client.send_did_close(uri)


async def main():
    root_path = Path().resolve()
    client = PyrightLSPClient(path_to_file_uri(str(root_path)))
    await client.start()

    # 启动监听文件变化任务
    asyncio.create_task(watch_and_sync(client, root_path))

    # 这里可以继续你的业务逻辑，比如调用 references 等

    # 主程序持续运行
    while True:
        await asyncio.sleep(2)  # 3600


if __name__ == "__main__":
    asyncio.run(main())
