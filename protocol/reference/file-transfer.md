---
name: COS transfer pattern
description: Use COS object storage to transfer large files between UISZ and other machines — Tailscale direct is too slow
type: memory
tags: [infra, transfer]
---


大文件在 UISZ ↔ 其他机器间传输，走 COS 中转而非 Tailscale/SSH 直传。

**Why:** Tailscale 直连带宽约 300KB/s，SSH pipe 在 ~32MB 处反复卡死。COS 上传/下载均走公网高速通道，524MB 仅需约 1 分钟。

**How to apply:**
```python
# UISZ 上传
import boto3
from botocore.config import Config
client = boto3.client("s3",
    endpoint_url="https://cos.ap-singapore.myqcloud.com",
    aws_access_key_id=TENCENT_SECRET_ID,
    aws_secret_access_key=TENCENT_SECRET_KEY,
    config=Config(signature_version="s3v4", region_name="ap-singapore", s3={"addressing_style": "virtual"})
)
client.upload_file(local_path, "operator-backup-EXAMPLE", "tmp/file.tar.gz")

# 本地下载（同 client 配置）
client.download_file("operator-backup-EXAMPLE", "tmp/file.tar.gz", local_path)
```
注意：presigned URL 在 COS 上行为不稳定，直接用 SDK download_file 更可靠。
